from __future__ import annotations

from pathlib import Path

from collector import collect_country
from country_source import fetch_un_member_states, save_country_list, CountrySourceError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATED_COUNTRIES_FILE = PROJECT_ROOT / "data" / "countries_generated.txt"


def load_countries_from_file(file_path: Path) -> list[str]:
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def get_countries() -> list[str]:
    try:
        countries = fetch_un_member_states()
        save_country_list(str(GENERATED_COUNTRIES_FILE), countries)
        print(f"[OK] Loaded {len(countries)} countries from online source.")
        print(f"[OK] Saved generated list to: {GENERATED_COUNTRIES_FILE}")
        return countries
    except CountrySourceError as e:
        print(f"[WARN] Online fetch failed: {e}")

        countries = load_countries_from_file(GENERATED_COUNTRIES_FILE)
        if countries:
            print(f"[OK] Loaded {len(countries)} countries from fallback file: {GENERATED_COUNTRIES_FILE}")
            return countries

        raise RuntimeError(
            "Could not load countries from online source or fallback file."
        ) from e


def main() -> None:
    try:
        countries = get_countries()
    except Exception as e:
        print(f"[FAIL] {e}")
        return

    for country in countries:
        try:
            paths = collect_country(country)
            print(f"[OK] {country}")
            for label, path in paths.items():
                print(f"   {label}: {path}")
        except Exception as e:
            print(f"[FAIL] {country}: {e}")


if __name__ == "__main__":
    main()