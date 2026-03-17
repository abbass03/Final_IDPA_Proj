from collector import collect_country

paths = collect_country("France")

for label, path in paths.items():
    print(f"{label}: {path}")