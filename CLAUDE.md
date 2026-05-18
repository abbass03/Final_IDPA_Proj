# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an academic research project implementing **Tree Edit Distance (TED)** algorithms for comparing Wikipedia country infoboxes. It parses semi-structured infobox data into rooted ordered labeled trees, computes edit distances between trees, generates edit scripts, applies patches, and presents results through a web UI.

**Stack:** Python 3.12.1, BeautifulSoup4, Requests, vanilla JS/HTML/CSS frontend, no web framework (custom HTTP server).

## Commands

### Run XML comparison pipeline
```bash
python src/main.py <source.xml> <target.xml> [custom|chawathe|nj]
# Example:
python src/main.py data/normalized_xml/lebanon.xml data/normalized_xml/switzerland.xml custom
```

### Run Wiki infobox comparison pipeline
```bash
python src/wiki_main.py <source.wiki> <target.wiki> [custom|chawathe|nj]
# Example:
python src/wiki_main.py data/original_infobox_source/lebanon_infobox.wiki data/original_infobox_source/switzerland_infobox.wiki nj
```

### Launch the interactive web UI
```bash
python src/ui_server.py
# Serves at http://127.0.0.1:8765
```

### Run tests
```bash
python -m unittest discover tests/
# Run a single test module:
python -m unittest tests.test_preprocess
```

### Build/refresh the Wikipedia dataset
```bash
python src/build_dataset.py   # fetches ~200 UN member states' infoboxes
```

### Visualize trees
```bash
python src/visualize_trees.py xml <source.xml> <target.xml> [method]
python src/visualize_trees.py wiki <source.wiki> <target.wiki> [method]
```

## Architecture

### Data flow
```
Raw Wikipedia HTML → collector.py → raw XML/JSON/wiki markup
                                  ↓
                    build_dataset.py → normalized_xml/, original_infobox_source/
                                  ↓
        parser.py (XML) / wiki_parser.py (wiki) → Node tree
                                  ↓
                    preprocess.py / semantic_values.py → normalized Node tree
                                  ↓
              ted.py → [ted_custom.py | ted_adapter.py → lit_ted/]
                                  ↓
                    Edit script (Insert/Delete/Update/Match ops)
                                  ↓
                    patch.py / lit_ted/patch.py → reconstructed target tree
                                  ↓
          postprocess.py / wiki_serializer.py → XML, JSON, wiki, report files
```

### Two tree representations (important)
- **`Node`** (`src/models.py`) — custom dataclass with `label`, `node_type`, `value`, `children`. Used throughout the custom pipeline and as the base representation.
- **`TreeNode`** (`src/lit_ted/tree.py`) — structured node for the literature TED algorithms (Chawathe, NJ). `ted_adapter.py` converts `Node` → `TreeNode`.

### Three TED algorithm implementations
| Method | File | Best for |
|---|---|---|
| `custom` | `src/ted_custom.py` | XML inputs; fastest |
| `chawathe` | `src/lit_ted/chawathe.py` | XML; depth-aware |
| `nj` | `src/lit_ted/nj.py` | Wiki infoboxes; recommended for production |

The unified dispatcher is `src/ted.py` which calls `ted_custom.py` for `custom` or `ted_adapter.py` → `src/lit_ted/ted.py` for the other two.

### Central orchestration
`src/comparison_service.py` is the single entry point for all comparison logic. It sequences: parse → preprocess → TED → patch → postprocess. Both `main.py` and `wiki_main.py` delegate to this service. The web UI calls it via `ui_server.py`.

### Preprocessing (`src/preprocess.py`, `src/semantic_values.py`)
Typed value normalization runs before TED:
- Dates → ISO 8601 (`YYYY-MM-DD`)
- Measurements → numeric + unit children
- Text → tokenized children
This creates structured child nodes so TED captures semantic changes rather than raw string diffs.

### Web UI (`src/ui_server.py`, `ui/`)
Custom `http.server`-based server (no Flask). The frontend (`ui/app.js`) sends comparison requests to the server via fetch, which runs the Python pipeline in-process and returns JSON. The UI provides mode/method selection, file picking, and tabbed artifact inspection (trees, edit scripts, patched output, metrics).

### Data directories
- `data/normalized_xml/` — preprocessed XML inputs (ready to compare)
- `data/original_infobox_source/` — raw `.wiki` infobox files
- `data/output/` — comparison results (gitignored)
- `data/raw_xml/`, `data/raw_json/`, `data/raw/` — intermediate scraped data
