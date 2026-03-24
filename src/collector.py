from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests


WIKIPEDIA_BASE = "https://en.wikipedia.org/wiki/"


def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())


def clean_tag(tag: str) -> str:
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
    text = re.sub(r"\[[^\]]*\]", "", text)   # remove [1], [a], [c]
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
    }

    for key, value in known_sections.items():
        if key in section:
            return value

    return None


def normalize_country_name_for_wikipedia(country_name: str) -> str:
    """
    Normalize some names from the country list into titles that Wikipedia pages expect.
    """
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
                sleep_seconds = 1.5 * attempt
                time.sleep(sleep_seconds)

    raise last_exc if last_exc is not None else RuntimeError(f"Failed to fetch {url}")


def extract_infobox_raw(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", class_=lambda c: c and "infobox" in c)
    if table is None:
        raise ValueError("No infobox found")

    data = {}

    for row in table.find_all("tr"):
        header = row.find("th")
        value = row.find("td")

        if header and value:
            key = " ".join(header.stripped_strings)
            val = " ".join(value.stripped_strings)
            data[key] = val

    return data


def extract_infobox_normalized(html: str) -> dict:
    """
    Extract infobox rows and normalize ambiguous labels using section context.
    """
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", class_=lambda c: c and "infobox" in c)
    if table is None:
        raise ValueError("No infobox found")

    data = {}
    current_section = None

    ambiguous_keys = {
        "total",
        "per_capita",
        "water",
        "density",
        "estimate",
        "urban",
        "rural",
    }

    for row in table.find_all("tr"):
        header = row.find("th")
        value = row.find("td")

        if header and value:
            raw_key = " ".join(header.stripped_strings)
            raw_value = " ".join(value.stripped_strings)

            key = clean_tag(raw_key)
            val = clean_value(raw_value)

            if not key or not val:
                continue

            if current_section and key in ambiguous_keys:
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

            data[key] = val

        elif header and not value:
            section_name = " ".join(header.stripped_strings)
            current_section = normalize_context(section_name)

    return data


def save_country_json(country_name: str, data: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{safe_filename(country_name)}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return filename


def dict_to_xml(country_name: str, data: dict) -> ET.Element:
    root = ET.Element("country")

    name_elem = ET.SubElement(root, "name")
    name_elem.text = clean_xml_text(country_name)

    for key, value in data.items():
        tag = clean_tag(key)
        if not tag:
            continue

        child = ET.SubElement(root, tag)
        child.text = clean_xml_text(value)

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

    raw_json_path = save_country_json(country_name, raw_data, "data/raw_json")
    raw_xml_path = save_country_xml(country_name, raw_data, "data/raw_xml")

    normalized_json_path = save_country_json(country_name, normalized_data, "data/normalized_json")
    normalized_xml_path = save_country_xml(country_name, normalized_data, "data/normalized_xml")

    return {
        "raw_json": raw_json_path,
        "raw_xml": raw_xml_path,
        "normalized_json": normalized_json_path,
        "normalized_xml": normalized_xml_path,
    }