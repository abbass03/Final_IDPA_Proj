import subprocess

pairs = [
    ("data/normalized_xml/lebanon.xml", "data/normalized_xml/switzerland.xml"),
    ("data/normalized_xml/france.xml", "data/normalized_xml/germany.xml"),
    ("data/normalized_xml/japan.xml", "data/normalized_xml/germany.xml"),
]

for a, b in pairs:
    print("=" * 70)
    print("Comparing:")
    print(" ", a)
    print(" ", b)
    print("=" * 70)

    subprocess.run(["python", "src/main.py", a, b])