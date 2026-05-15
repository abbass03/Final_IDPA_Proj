from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MONTH_PATTERN = "|".join(MONTHS.keys())

NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
MEASUREMENT_RE = re.compile(
    r"^(?P<currency>[$€£¥])?\s*"
    r"(?P<number>[+-]?\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(?P<unit>[A-Za-z%°/][A-Za-z0-9%°/\-]*))?$"
)
TOKEN_RE = re.compile(
    r"\d[\d,]*(?:\.\d+)?|[A-Za-z]+\d+|[A-Za-z]+(?:[-'][A-Za-z]+)*|[%$€£¥°/]+|\S"
)


def normalize_surface_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ")
    text = text.replace("′", "'").replace("’", "'").replace("″", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_numeric_token(token: str) -> str:
    return token.replace(",", "")


def tokenize_text(text: str) -> list[str]:
    text = normalize_surface_text(text)
    if not text:
        return []
    return TOKEN_RE.findall(text)


def parse_date_components(text: str) -> dict[str, str] | None:
    text = normalize_surface_text(text)

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return {
                "year": f"{parsed.year:04d}",
                "month": f"{parsed.month:02d}",
                "day": f"{parsed.day:02d}",
            }
        except ValueError:
            continue

    month_name = re.fullmatch(
        rf"(?i)(?P<day>\d{{1,2}})\s+(?P<month>{MONTH_PATTERN})\s+(?P<year>\d{{4}})",
        text,
    )
    if month_name:
        month = MONTHS[month_name.group("month").lower()]
        return {
            "year": month_name.group("year"),
            "month": f"{month:02d}",
            "day": f"{int(month_name.group('day')):02d}",
        }

    month_first = re.fullmatch(
        rf"(?i)(?P<month>{MONTH_PATTERN})\s+(?P<day>\d{{1,2}}),?\s+(?P<year>\d{{4}})",
        text,
    )
    if month_first:
        month = MONTHS[month_first.group("month").lower()]
        return {
            "year": month_first.group("year"),
            "month": f"{month:02d}",
            "day": f"{int(month_first.group('day')):02d}",
        }

    year_only = re.fullmatch(r"\d{4}", text)
    if year_only:
        return {"year": year_only.group(0)}

    return None


def parse_measurement(text: str) -> dict[str, str] | None:
    text = normalize_surface_text(text)
    if parse_date_components(text) is not None:
        return None

    match = MEASUREMENT_RE.fullmatch(text)
    if not match:
        return None

    number = normalize_numeric_token(match.group("number"))
    if not NUMBER_RE.fullmatch(number):
        return None

    data = {"number": number}

    currency = match.group("currency")
    if currency:
        data["currency"] = currency

    unit = match.group("unit")
    if unit:
        data["unit"] = unit.lower()

    return data


def classify_token(token: str) -> str:
    cleaned = normalize_surface_text(token)
    lowered = cleaned.lower()

    if NUMBER_RE.fullmatch(cleaned.replace(",", "")):
        return "number_token"
    if lowered in MONTHS:
        return "month_token"
    if lowered in {"n", "s", "e", "w", "ne", "nw", "se", "sw"}:
        return "direction_token"
    if re.fullmatch(r"[%$€£¥°/]+", cleaned):
        return "symbol_token"
    if re.fullmatch(r"[-:'\"]", cleaned):
        return "symbol_token"
    if re.fullmatch(r"[A-Za-z]+[0-9]+", cleaned) or lowered in {
        "km",
        "km2",
        "km3",
        "m",
        "m2",
        "m3",
        "mi",
        "mi2",
        "percent",
    }:
        return "unit_token"
    return "word_token"


def semantic_signature(value: str | None) -> dict[str, Any]:
    if value is None:
        return {"kind": "empty", "text": ""}

    text = normalize_surface_text(str(value))
    if text == "":
        return {"kind": "empty", "text": ""}

    date_parts = parse_date_components(text)
    if date_parts is not None:
        return {"kind": "date", "text": text, "parts": date_parts}

    measurement = parse_measurement(text)
    if measurement is not None:
        number = float(measurement["number"])
        return {
            "kind": "measurement",
            "text": text,
            "number": number,
            "unit": measurement.get("unit"),
            "currency": measurement.get("currency"),
        }

    tokens = tokenize_text(text)
    normalized_tokens = [
        normalize_numeric_token(token).lower() if classify_token(token) == "number_token"
        else normalize_surface_text(token).lower()
        for token in tokens
    ]
    return {"kind": "text", "text": text, "tokens": normalized_tokens}


def normalize_text_value(text: str) -> str:
    text = normalize_surface_text(text)

    date_parts = parse_date_components(text)
    if date_parts is not None:
        if {"year", "month", "day"} <= set(date_parts):
            return f"{date_parts['year']}-{date_parts['month']}-{date_parts['day']}"
        return date_parts["year"]

    measurement_parts = parse_measurement(text)
    if measurement_parts is not None:
        pieces = []
        if "currency" in measurement_parts:
            pieces.append(measurement_parts["currency"])
        pieces.append(measurement_parts["number"])
        if "unit" in measurement_parts:
            pieces.append(measurement_parts["unit"])
        return " ".join(pieces)

    tokens = tokenize_text(text)
    return " ".join(tokens) if tokens else text


def semantic_value_distance(left: str | None, right: str | None) -> int:
    if (left or "") == (right or ""):
        return 0

    a = semantic_signature(left)
    b = semantic_signature(right)

    if a["kind"] != b["kind"]:
        return 2

    if a["kind"] == "empty":
        return 0

    if a["kind"] == "date":
        pa = a["parts"]
        pb = b["parts"]
        if pa == pb:
            return 0
        if pa.get("year") == pb.get("year") and pa.get("month") == pb.get("month"):
            return 1
        if pa.get("year") == pb.get("year"):
            return 2
        return 3

    if a["kind"] == "measurement":
        if a.get("unit") != b.get("unit") or a.get("currency") != b.get("currency"):
            return 2

        left_num = float(a["number"])
        right_num = float(b["number"])
        baseline = max(abs(left_num), abs(right_num), 1.0)
        relative_delta = abs(left_num - right_num) / baseline

        if relative_delta <= 0.01:
            return 0
        if relative_delta <= 0.10:
            return 1
        if relative_delta <= 0.50:
            return 2
        return 3

    tokens_a = set(a["tokens"])
    tokens_b = set(b["tokens"])
    if not tokens_a and not tokens_b:
        return 0

    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    similarity = intersection / union if union else 1.0

    if similarity >= 0.85:
        return 0
    if similarity >= 0.50:
        return 1
    if intersection > 0:
        return 2
    return 3
