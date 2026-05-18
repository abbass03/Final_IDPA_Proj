# Wikipedia Infobox Comparison, Tree Edit Distance, and Country Clustering

This project is a full IDPA workflow for collecting, normalizing, comparing, and analyzing country infobox data. It combines XML processing, Wikipedia infobox extraction, Tree Edit Distance (TED), edit-script generation, patch validation, distance-matrix construction, and clustering analysis in one repository.

The core idea is to represent each country infobox as a rooted ordered labeled tree, compare two trees with TED, explain the transformation through edit operations, and then scale the same representation to compare many countries at once.

## What the Project Does

- collects country infobox data from Wikipedia
- stores both raw and normalized country representations
- converts structured data into tree form
- applies semantic preprocessing to values like dates and measurements
- compares two trees with multiple TED algorithms
- generates edit scripts and patches one tree into another
- exports comparison results in human-readable and machine-readable formats
- builds pairwise country distance matrices
- runs clustering algorithms on the resulting country-similarity space

## Main Components

### 1. Data collection and normalization

The collection pipeline fetches Wikipedia country pages, extracts infobox rows, cleans noisy text, normalizes inconsistent field names, and writes outputs in both JSON and XML.

Important parts of this stage include:

- raw infobox extraction from HTML
- normalized field naming for sections like GDP, population, area, Gini, and HDI
- XML-safe cleaning of values
- conversion into nested structured representations

This logic is implemented mainly in `src/collector.py`.

### 2. Tree representation

After parsing, each document is represented as a tree of nodes. Each node can carry:

- a label
- a value
- child nodes

This gives the project a common structure for comparing both normalized XML files and Wikipedia infobox source files.

### 3. Semantic preprocessing

Before running TED, the project performs value-aware preprocessing so comparisons are more meaningful than plain string matching.

Examples:

- dates such as `14 May 2026` are normalized into structured date components
- measurements such as `10,452 km2` are split into number and unit information
- text is tokenized and normalized for semantic comparison

This improves TED update costs by distinguishing small, moderate, and major value differences.

Relevant files:

- `src/preprocess.py`
- `src/semantic_values.py`

### 4. Tree Edit Distance

The project supports three TED strategies:

- `custom`: the project’s own TED implementation
- `chawathe`: a literature-based tree comparison approach
- `nj`: a Nierman-Jagadish style method

These methods are unified behind the comparison pipeline so the same input data can be tested across algorithms.

Relevant files:

- `src/ted.py`
- `src/ted_custom.py`
- `src/ted_adapter.py`
- `src/lit_ted/`

### 5. Edit scripts and patching

After computing TED, the project records edit operations such as:

- insert
- delete
- update

It then applies those operations to reconstruct the target tree from the source tree. Patch success is used as a correctness check for the generated edit script.

Relevant files:

- `src/diff.py`
- `src/patch.py`
- `src/comparison_service.py`

### 6. Scaling to many countries

Beyond pairwise comparison, the project builds full distance matrices across country datasets and uses them for clustering and conclusions analysis.

This lets the project answer questions like:

- which countries are structurally similar in their infobox representation
- whether natural clusters exist in the data
- which TED method produces the most useful large-scale similarity structure

Relevant files:

- `src/build_distance_matrix.py`
- `src/distance_matrix.py`
- `src/cluster_service.py`
- `src/clustering.py`
- `src/run_conclusions_analysis.py`

## Repository Structure

```text
IDPA_Proj/
|- src/                         Core logic, pipelines, TED, clustering, UI server
|- tests/                       Unit tests
|- ui/                          Browser UI files
|- data/
|  |- normalized_xml/           Normalized XML country files
|  |- normalized_json/          Normalized JSON country files
|  |- raw_xml/                  Raw collected XML files
|  |- raw_json/                 Raw collected JSON files
|  |- original_infobox_source/  Saved Wikipedia infobox source blocks
|  |- preprocessed_trees/       Cached preprocessed tree data
|  |- output/                   Generated comparison outputs
|  `- *.json / *.png / reports  Distance matrices and analysis artifacts
`- Readme.md
```

## Supported Workflows

### XML comparison workflow

This compares two normalized XML country files, preprocesses their trees, computes TED, generates edit operations, applies the patch, and exports the results.

Example:

```powershell
python src\main.py data\normalized_xml\lebanon.xml data\normalized_xml\switzerland.xml custom
```

### Wikipedia infobox workflow

This compares two saved Wikipedia infobox source files using the same general TED pipeline but with the wiki parser and serializer.

Example:

```powershell
python src\wiki_main.py data\original_infobox_source\lebanon_infobox.wiki data\original_infobox_source\switzerland_infobox.wiki nj
```

### Interactive UI workflow

The local UI exposes both comparison and clustering features through a browser interface.

Run:

```powershell
python src\ui_server.py
```

Then open:

```text
http://127.0.0.1:8765
```

The UI supports:

- selecting XML or wiki mode
- choosing a TED method
- browsing available input files
- viewing source content
- running comparisons interactively
- inspecting generated outputs
- running clustering on country subsets
- adding a custom XML country file during the session

## Outputs

Depending on the mode, the project writes outputs under `data/output/`.

Typical outputs include:

- edit-script JSON
- normalized tree XML
- normalized tree JSON
- patched tree XML and JSON
- infobox-text exports
- comparison reports

The comparison service also returns structured in-memory results for UI usage, including:

- node counts
- tree-edit distance
- similarity score
- operation summaries
- patch success or first mismatch

## Distance Matrix and Clustering

The project can compare many countries at once by building a pairwise distance matrix from the normalized XML dataset.

Example commands:

```powershell
python src\build_distance_matrix.py --method nj
```

```powershell
python src\build_distance_matrix.py --method chawathe --quick 20
```

```powershell
python src\build_distance_matrix.py --method chawathe --preprocess
```

Once a matrix exists, the clustering layer can run:

- Agglomerative Hierarchical Clustering
- K-Medoids
- K-Means on MDS coordinates
- DBSCAN

It also evaluates clustering quality with:

- silhouette score
- Dunn index
- Hopkins statistic in the conclusions script

## Conclusions and Analysis

The repository includes analysis scripts for interpreting the country-distance space rather than only computing it.

The conclusions workflow explores:

- k-value sweeps for K-Medoids
- AHC behavior under different cluster counts
- cluster compactness and separation
- geographic interpretation of cluster medoids
- whether the dataset shows strong natural clustering

Run:

```powershell
python src\run_conclusions_analysis.py
```

## Setup

Recommended environment:

- Python 3.10 or newer
- virtual environment

Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install requests beautifulsoup4 numpy
```

Main dependency purposes:

- `requests`: fetch Wikipedia pages
- `beautifulsoup4`: extract infobox data from HTML
- `numpy`: MDS support for clustering visualization and analysis

## Testing

Run the unit tests with:

```powershell
python -m unittest discover -s tests
```

The current tests focus on:

- preprocessing behavior
- semantic value parsing
- collector normalization

## Design Rationale

This project was designed to bridge two goals:

- precise pairwise structural comparison
- large-scale exploratory analysis across many countries

Using trees makes it possible to preserve document structure instead of flattening everything into strings or tables. Adding semantic preprocessing makes the comparison more realistic for values that carry internal meaning, such as dates, currencies, units, and tokenized phrases. The patching stage then provides a practical correctness signal: if the edit script can reconstruct the target tree, the TED result is not only numerical but operationally validated.

## Recommended Demo Paths

- For normalized XML demos, use `custom` or `chawathe`
- For Wikipedia infobox demos, use `nj`
- For interactive exploration, use `src\ui_server.py`
- For large-scale analysis, use the precomputed matrix files already stored under `data/`

## Author

Abbas Abdallah-Hasan Bazzi
