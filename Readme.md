# Tree Edit Distance for Country Infobox Comparison

This project compares country information using **Tree Edit Distance (TED)** with two different representations:

1. **XML-based country data**
2. **Wikipedia infobox wikitext**

The system parses each representation into trees, computes structural differences, generates edit scripts, and applies patch operations to transform one country tree into another.

---

## Table of Contents

- [Project Idea](#project-idea)
- [Objectives](#objectives)
- [Approaches](#approaches)
- [Project Structure](#project-structure)
- [How the Pipeline Works](#how-the-pipeline-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [How to Run](#how-to-run)
- [Testing](#testing)
- [Evaluation](#evaluation)
- [Outputs](#outputs)
- [Current Results](#current-results)
- [Limitations](#limitations)
- [Future Work](#future-work)
- [Author](#author)
- [License](#license)

---

## Project Idea

Country information often appears in semi-structured formats such as XML files and Wikipedia infoboxes. These formats contain similar information, but they differ in structure, ordering, labels, and formatting.

This project studies how to compare such data using **Tree Edit Distance** by:

- converting country data into trees
- measuring structural and value differences
- generating edit scripts
- applying patches to reconstruct target trees
- comparing the reliability of XML and wiki-infobox representations

---

## Objectives

The main goals of this project are:

- parse country data into tree structures
- compute tree edit distance between two countries
- generate edit operations:
  - `insert`
  - `delete`
  - `update`
- apply the generated edit script to transform one tree into another
- evaluate the method on multiple country pairs
- compare the XML approach with the wiki-infobox approach

---

## Approaches

### 1. XML Approach

The XML approach works on structured country XML files.

**Pipeline**
- parse raw XML
- preprocess/normalize the tree
- compute TED
- generate edit script
- apply patch
- evaluate reconstruction quality

**Strengths**
- cleaner structure
- more stable patching
- easier parsing
- stronger reconstruction performance

**Limitations**
- less close to original Wikipedia source formatting

---

### 2. Wiki Infobox Approach

The wiki approach works directly on infobox wikitext extracted from Wikipedia.

**Pipeline**
- fetch page wikitext
- extract infobox block
- parse infobox into a tree
- compute TED
- generate edit script
- apply patch
- serialize back into infobox-like wikitext

**Supported wiki value types**
- plain text
- internal links such as `[[Beirut]]`
- templates such as `{{flag|Lebanon}}`
- `<br>`-separated values

**Strengths**
- closer to the original semi-structured source
- more realistic representation of Wikipedia data

**Limitations**
- parsing is harder
- patch reconstruction is less stable on large real infoboxes
- repeated labels and nested markup make paths fragile

---

## Project Structure

```text
Project1/
├── data/
│   ├── normalized_json/
│   ├── normalized_xml/
│   ├── original_infobox_source/
│   ├── output/
│   ├── raw/
│   ├── raw_json/
│   ├── raw_wikitext/
│   ├── raw_xml/
│   └── countries.txt
│
├── src/
│   ├── build_dataset.py
│   ├── collector.py
│   ├── diff.py
│   ├── evaluate_wiki_pipeline.py
│   ├── evaluate_xml_pipeline.py
│   ├── main.py
│   ├── models.py
│   ├── parser.py
│   ├── patch.py
│   ├── postprocess.py
│   ├── preprocess.py
│   ├── run_examples.py
│   ├── ted.py
│   ├── test_collect.py
│   ├── test_wiki_pipeline.py
│   ├── test_wiki_source.py
│   ├── utils.py
│   ├── wiki_main.py
│   ├── wiki_parser.py
│   ├── wiki_serializer.py
│   └── wiki_source.py
│
└── README.md


How the Pipeline Works
General TED workflow

-For both approaches, the core workflow is:
-load source country data
-load target country data
-parse each into a tree
-compute tree edit distance
-generate an edit script
-apply the edit script to the source tree
-compare the patched tree with the target tree

XML workflow

-read XML file
-parse XML into internal Node tree
-preprocess/normalize the tree
-compute TED and edit operations
-patch source tree
-compare patched tree to target tree


Wiki workflow

-fetch or load infobox wikitext
-extract infobox template
-parse infobox into internal Node tree
-compute TED and edit operations
-patch source tree
-serialize patched tree if needed
-compare patched tree to target tree


Requirements

-Python 3.10 or newer
-Windows PowerShell or any terminal
-Internet access only if you want to fetch Wikipedia infoboxes live
-This project mainly uses Python standard libraries. If you created a virtual environment, activate it before running.


Installation
1. Clone or open the project

If you already have the project locally, go into the folder.
cd Project1

2. Create a virtual environment
python -m venv .venv

3. Activate the virtual environment
Windows PowerShell
.\.venv\Scripts\Activate.ps1
Windows CMD
.\.venv\Scripts\activate.bat




How to Run

Run the XML pipeline
python .\src\main.py

This runs the XML-based tree comparison pipeline.

Run the Wiki pipeline

python .\src\test_wiki_source.py
python src/wiki_main.py data/original_infobox_source/lebanon_infobox.wiki data/original_infobox_source/switzerland_infobox.wiki

This runs the wiki-infobox tree comparison pipeline.

Generate wiki infobox files

To fetch infoboxes from Wikipedia and save them into:

data/original_infobox_source/

run:

python .\src\test_wiki_source.py

You can edit the country list inside test_wiki_source.py to generate more countries.

Example expected files:

lebanon_infobox.wiki

switzerland_infobox.wiki

france_infobox.wiki

germany_infobox.wiki

japan_infobox.wiki




Testing
Test collection logic
python .\src\test_collect.py
Test the wiki pipeline
python .\src\test_wiki_pipeline.py

These tests check:

parse → serialize → parse round-trip stability

zero TED for identical trees

patch reconstruction on small examples

preservation of links

preservation of templates

Expected output:

All wiki pipeline tests passed.
Evaluation
Evaluate XML approach
python .\src\evaluate_xml_pipeline.py

This reports for each pair:

source country

target country

source node count

target node count

TED

similarity score

patch success

Example output:

source       target       nodes_source  nodes_target  ted      similarity   patch_success
------------------------------------------------------------------------------------------
Lebanon      Switzerland  77            83            68       0.575        True
France       Germany      65            51            43       0.6293       True
Germany      Japan        51            53            37       0.6442       True


Evaluate Wiki approach
python .\src\evaluate_wiki_pipeline.py

This evaluates the wiki-infobox pipeline on the available infobox files.

Because the wiki representation is more complex, TED computation works well, but exact patch reconstruction may fail on large real-world examples.


Outputs

Depending on the script you run, the project can generate outputs such as:

parsed or normalized trees

edit scripts in JSON

patched XML or wiki trees

serialized wiki infobox text

evaluation summaries



The project uses a normalized similarity score:

similarity = 1 - TED / (nodes_source + nodes_target)

Interpretation:

closer to 1.0 means more similar

lower values mean more structural and textual difference

Current Results
XML approach

The XML approach is currently the more stable and reliable one.

Observed behavior:

exact patch reconstruction succeeded on most tested country pairs

tree edit distance values were consistent and meaningful

XML trees were easier to parse and patch than wiki trees

Example result summary:

successful exact reconstruction in most tested cases

one direction-dependent failure suggests patch sensitivity in some asymmetric cases



Wiki approach

The wiki approach successfully:

parses real infoboxes

computes TED

generates edit scripts

handles links and templates better than the initial version

However, exact patch reconstruction on large real-world infoboxes is still unstable.



This is mainly due to:

repeated labels

nested wiki structure

fragile label-based path targeting during patching


