import os
import requests
import re

API_URL = "https://en.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": "IDPA-Project/1.0 (student project)"
}

def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())

def fetch_page_wikitext(title: str) -> str:
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title.replace(" ", "_"),
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()

    pages = data["query"]["pages"]
    if not pages or "missing" in pages[0]:
        raise ValueError(f"Page not found: {title}")

    revs = pages[0].get("revisions", [])
    if not revs:
        raise ValueError(f"No revision content for: {title}")

    return revs[0]["slots"]["main"]["content"]

def save_wikitext(title: str, text: str, out_dir: str = "data/raw_wikitext") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{safe_filename(title)}.wiki")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def extract_infobox_block(page_text: str) -> str:
    start = page_text.find("{{Infobox")
    if start == -1:
        raise ValueError("Infobox template not found")

    depth = 0
    i = start
    while i < len(page_text) - 1:
        pair = page_text[i:i+2]

        if pair == "{{":
            depth += 1
            i += 2
            continue

        if pair == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return page_text[start:i]
            continue

        i += 1

    raise ValueError("Unclosed infobox template")

def save_infobox_block(title: str, text: str, out_dir: str = "data/original_infobox_source") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{safe_filename(title)}_infobox.wiki")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
