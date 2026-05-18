# Final IDPA Project

This repository contains the full IDPA project inside the [`IDPA_Proj`](./IDPA_Proj) folder.

## Main Project

Open [`IDPA_Proj/Readme.md`](./IDPA_Proj/Readme.md) for the complete project documentation, including:

- project overview
- setup instructions
- XML and Wikipedia comparison pipelines
- local UI usage
- clustering and analysis scripts
- test commands

## Quick Start

```powershell
cd IDPA_Proj
python -m venv .venv
.venv\Scripts\activate
pip install requests beautifulsoup4 numpy
python src\ui_server.py
```

Then open `http://127.0.0.1:8765`.
