from collector import collect_country

def load_countries(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

countries = load_countries("data/countries.txt")

for country in countries:
    try:
        paths = collect_country(country)
        print(f"[OK] {country}")
        for label, path in paths.items():
            print(f"   {label}: {path}")
    except Exception as e:
        print(f"[FAIL] {country}: {e}")