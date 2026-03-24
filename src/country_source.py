from __future__ import annotations

from typing import List
import requests


API_URL = "https://en.wikipedia.org/w/api.php"
CATEGORY_TITLE = "Category:Member states of the United Nations"

HEADERS = {
    "User-Agent": "IDPA_Project/1.0 (educational project)"
}

EXCLUDED_TITLES = {
    "Member states of the United Nations",
}


class CountrySourceError(RuntimeError):
    pass


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def normalize_titles(titles: List[str]) -> List[str]:
    cleaned: List[str] = []

    for title in titles:
        t = title.strip()

        if not t or t in EXCLUDED_TITLES:
            continue

        cleaned.append(t)

    unique = _dedupe_keep_order(cleaned)

    # Keep the country form used for infobox fetching
    if "Netherlands" in unique and "Kingdom of the Netherlands" in unique:
        unique.remove("Kingdom of the Netherlands")

    return unique


def fetch_un_member_states() -> List[str]:
    """
    Build the UN-member-state country list using the Wikipedia API category
    'Member states of the United Nations'.

    Returns:
        List[str]: 193 country titles suitable for fetching Wikipedia pages.
    """
    titles: List[str] = []
    cmcontinue: str | None = None

    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": CATEGORY_TITLE,
            "cmnamespace": 0,   # article pages only
            "cmlimit": "max",
            "format": "json",
        }

        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        try:
            response = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            raise CountrySourceError(f"Failed to fetch country list from Wikipedia API: {exc}") from exc

        data = response.json()

        members = data.get("query", {}).get("categorymembers", [])
        for member in members:
            title = member.get("title", "").strip()
            if title:
                titles.append(title)

        if "continue" not in data:
            break

        cmcontinue = data["continue"]["cmcontinue"]

    final_titles = normalize_titles(titles)

    if len(final_titles) != 193:
        raise CountrySourceError(
            f"Expected 193 countries, but got {len(final_titles)}."
        )

    return final_titles


def save_country_list(file_path: str, countries: List[str]) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        for country in countries:
            f.write(country + "\n")


if __name__ == "__main__":
    countries = fetch_un_member_states()
    print(f"Fetched {len(countries)} countries.")
    for name in countries[:30]:
        print("-", name)