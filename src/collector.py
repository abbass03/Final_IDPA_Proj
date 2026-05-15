from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import requests


WIKIPEDIA_BASE = "https://en.wikipedia.org/wiki/"

SECTION_KEYS = (
    "gdp_ppp",
    "gdp_nominal",
    "population",
    "area",
    "gini",
    "hdi",
    "ethnic_groups",
    "religion",
    "coordinates",
)
AMBIGUOUS_KEYS = {
    "total",
    "per_capita",
    "water",
    "density",
    "estimate",
    "urban",
    "rural",
    "year",
    "rank",
}


def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())


def fix_mojibake(text: str) -> str:
    if not text:
        return text

    suspicious = ("Â", "Ã", "â", "ï»", "Ù", "Ø")
    if any(marker in text for marker in suspicious):
        try:
            repaired = text.encode("latin1").decode("utf-8")
            if repaired:
                return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return text


def clean_tag(tag: str) -> str:
    tag = fix_mojibake(tag)
    tag = tag.strip().lower()
    tag = tag.replace(" ", "_").replace("-", "_")
    tag = re.sub(r"[^a-z0-9_]", "", tag)
    tag = re.sub(r"_+", "_", tag)
    tag = tag.strip("_")

    if not tag:
        tag = "field"

    if not re.match(r"^[a-zA-Z_]", tag):
        tag = f"field_{tag}"

    return tag


def clean_value(text: str) -> str:
    text = fix_mojibake(text)
    text = text.replace("\xa0", " ")
    text = text.replace("﻿", "")
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_xml_text(text: str) -> str:
    text = clean_value(text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return text


def normalize_context(section: str | None) -> str | None:
    if not section:
        return None

    section = clean_tag(section)

    known_sections = {
        "area": "area",
        "population": "population",
        "gdp_ppp": "gdp_ppp",
        "gdp_nominal": "gdp_nominal",
        "government": "government",
        "gini": "gini",
        "hdi": "hdi",
        "ethnic_groups": "ethnic_groups",
        "religion": "religion",
        "coordinates": "coordinates",
    }

    for key, value in known_sections.items():
        if key in section:
            return value

    return None


def normalize_country_name_for_wikipedia(country_name: str) -> str:
    mapping = {
        "The Bahamas": "Bahamas",
        "Bolivia": "Bolivia",
        "Brunei": "Brunei",
        "Cape Verde": "Cabo Verde",
    }
    return mapping.get(country_name, country_name)


def fetch_country_page(country_name: str, max_retries: int = 4, timeout: int = 30) -> str:
    country_name = normalize_country_name_for_wikipedia(country_name)
    url_name = country_name.replace(" ", "_")
    url = WIKIPEDIA_BASE + url_name

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(1.5 * attempt)

    raise last_exc if last_exc is not None else RuntimeError(f"Failed to fetch {url}")


def extract_year(text: str) -> str | None:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return match.group(0) if match else None


def normalize_header_metadata(raw_key: str, current_section: str | None) -> tuple[str, dict[str, str], str | None]:
    header = clean_value(raw_key)
    annotations = [clean_value(part) for part in re.findall(r"\(([^)]*)\)", header)]
    header_without_parens = clean_value(re.sub(r"\([^)]*\)", "", header))

    section_guess = normalize_context(header) or normalize_context(header_without_parens)
    base_key = clean_tag(header_without_parens)
    extras: dict[str, str] = {}

    if base_key == "field" and current_section:
        lowered_annotations = " ".join(part.lower() for part in annotations)
        if "estimate" in lowered_annotations:
            base_key = f"{current_section}_estimate"
        elif annotations:
            base_key = f"{current_section}_{clean_tag(annotations[0])}"

    for part in annotations:
        lowered = part.lower()
        year = extract_year(part)
        if year is not None:
            extras["year"] = year

        if "estimate" in lowered:
            if base_key in {"population", "gdp_ppp", "gdp_nominal"}:
                base_key = f"{base_key}_estimate"
            elif current_section and base_key == "field":
                base_key = f"{current_section}_estimate"
        elif "census" in lowered and base_key == "population":
            base_key = "population_census"
        elif section_guess in {"gdp_ppp", "gdp_nominal"} and "rank" in lowered:
            base_key = f"{section_guess}_rank"

    if section_guess in {"gdp_ppp", "gdp_nominal"} and base_key not in {
        "gdp_ppp_total",
        "gdp_ppp_per_capita",
        "gdp_nominal_total",
        "gdp_nominal_per_capita",
    }:
        base_key = section_guess

    if base_key in {"gini", "hdi", "religion", "ethnic_groups"} and "year" in extras:
        extras[f"{base_key}_year"] = extras.pop("year")

    next_section = section_guess or current_section
    return base_key, extras, next_section


def extract_infobox_rows(html: str) -> list[tuple[str, str | None]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_=lambda c: c and "infobox" in c)
    if table is None:
        raise ValueError("No infobox found")

    rows: list[tuple[str, str | None]] = []
    for row in table.find_all("tr"):
        header = row.find("th")
        value = row.find("td")

        if not header:
            continue

        raw_key = " ".join(header.stripped_strings)
        raw_value = " ".join(value.stripped_strings) if value else None
        rows.append((raw_key, raw_value))

    return rows


def extract_infobox_raw(html: str) -> dict:
    data = {}

    for raw_key, raw_value in extract_infobox_rows(html):
        if raw_value is None:
            continue
        key = clean_value(raw_key)
        value = clean_value(raw_value)
        if key and value:
            data[key] = value

    return data


def extract_infobox_normalized(html: str) -> dict:
    data: dict[str, str] = {}
    current_section: str | None = None

    for raw_key, raw_value in extract_infobox_rows(html):
        key, extras, next_section = normalize_header_metadata(raw_key, current_section)
        current_section = next_section

        if raw_value is None:
            continue

        value = clean_value(raw_value)
        if not value:
            continue

        lowered_value = value.lower()

        if key in {"gdp_ppp", "gdp_nominal"}:
            year = extract_year(value)
            if year is not None:
                data[f"{key}_year"] = year
            if "estimate" in lowered_value:
                data[f"{key}_basis"] = "estimate"
            continue

        if key == "population" and "estimate" in lowered_value:
            key = "population_estimate"
            year = extract_year(value)
            if year is not None:
                data["population_estimate_year"] = year
            continue

        if current_section and key in AMBIGUOUS_KEYS:
            key = f"{current_section}_{key}"

        if key == "total" and current_section == "gdp_ppp":
            key = "gdp_ppp_total"
        elif key == "per_capita" and current_section == "gdp_ppp":
            key = "gdp_ppp_per_capita"
        elif key == "total" and current_section == "gdp_nominal":
            key = "gdp_nominal_total"
        elif key == "per_capita" and current_section == "gdp_nominal":
            key = "gdp_nominal_per_capita"
        elif key == "density" and current_section == "population":
            key = "population_density"
        elif key == "water" and current_section == "area":
            key = "area_water"
        elif key == "total" and current_section == "area":
            key = "area_total"

        data[key] = value
        for extra_key, extra_value in extras.items():
            if extra_key == "year":
                data[f"{key}_year"] = extra_value
            else:
                data[extra_key] = extra_value

    return data


def structure_normalized_data(data: dict[str, str]) -> dict:
    structured: dict[str, object] = {}

    for key, value in data.items():
        inserted = False

        for section in SECTION_KEYS:
            if key == section:
                bucket = structured.setdefault(section, {})
                if isinstance(bucket, dict):
                    bucket["value"] = value
                inserted = True
                break

            prefix = f"{section}_"
            if key.startswith(prefix):
                bucket = structured.setdefault(section, {})
                if isinstance(bucket, dict):
                    bucket[key[len(prefix):]] = value
                inserted = True
                break

        if not inserted:
            structured[key] = value

    return structured


def save_country_json(country_name: str, data: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{safe_filename(country_name)}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return filename


def append_xml_value(parent: ET.Element, key: str, value: object) -> None:
    child = ET.SubElement(parent, clean_tag(key))

    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            append_xml_value(child, sub_key, sub_value)
        return

    child.text = clean_xml_text(str(value))


def dict_to_xml(country_name: str, data: dict) -> ET.Element:
    root = ET.Element("country")

    name_elem = ET.SubElement(root, "name")
    name_elem.text = clean_xml_text(country_name)

    for key, value in data.items():
        append_xml_value(root, key, value)

    return root


def save_country_xml(country_name: str, data: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{safe_filename(country_name)}.xml")

    root = dict_to_xml(country_name, data)
    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)

    return filename


def collect_country(country_name: str) -> dict:
    html = fetch_country_page(country_name)

    raw_data = extract_infobox_raw(html)
    normalized_data = extract_infobox_normalized(html)
    structured_normalized = structure_normalized_data(normalized_data)

    raw_json_path = save_country_json(country_name, raw_data, "data/raw_json")
    raw_xml_path = save_country_xml(country_name, raw_data, "data/raw_xml")

    normalized_json_path = save_country_json(country_name, structured_normalized, "data/normalized_json")
    normalized_xml_path = save_country_xml(country_name, structured_normalized, "data/normalized_xml")

    return {
        "raw_json": raw_json_path,
        "raw_xml": raw_xml_path,
        "normalized_json": normalized_json_path,
        "normalized_xml": normalized_xml_path,
    }
