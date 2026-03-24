from wiki_source import fetch_page_wikitext, extract_infobox_block, save_infobox_block

countries = ["Lebanon", "Switzerland", "Albania", "France", "Germany", "Japan"]

for country in countries:
    page_text = fetch_page_wikitext(country)
    infobox_text = extract_infobox_block(page_text)
    path = save_infobox_block(country, infobox_text)
    print(f"{country}: {path}")