# 🌍 Wikipedia Infobox Comparison using Tree Edit Distance (TED)

## 📌 Overview

This project implements a complete system for **comparing, differencing, and transforming Wikipedia infoboxes** using **Tree Edit Distance (TED)**.

It converts infobox data into **rooted ordered labeled trees**, computes similarity between countries, extracts edit scripts, and reconstructs trees using patching.

The system supports:

* Structured **XML comparison**
* Real-world **Wikipedia infobox comparison**
* Multiple **TED algorithms**

---

## 🚀 Features

* 🔄 **Preprocessing**: Convert infobox data into tree structures
* 🌳 **Tree Representation**: Rooted ordered labeled trees
* 📏 **Tree Edit Distance (TED)**:

  * Custom TED
  * Chawathe algorithm
  * Nierman–Jagadish (NJ)
* 🔧 **Edit Script Extraction** (Insert, Delete, Update)
* 🧩 **Tree Patching** (reconstruct target tree)
* 📊 **Similarity Measurement**
* 📄 **Postprocessing Outputs**:

  * XML
  * JSON
  * Wikipedia infobox text
  * Comparison report
* 🌲 **Tree Visualization**

---

## 🏗️ Project Structure

```bash
src/
├── parser.py
├── preprocess.py
├── wiki_parser.py
├── wiki_source.py
├── ted.py
├── ted_custom.py
├── ted_adapter.py
├── diff.py
├── patch.py
├── utils.py
├── postprocess.py
├── main.py
├── wiki_main.py
├── visualize_trees.py

data/
├── normalized_xml/
├── original_infobox_source/
├── output/
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <project-folder>
```

### 2. Create virtual environment

```bash
python -m venv .venv
```

### 3. Activate environment

**Windows:**

```bash
.venv\Scripts\activate
```

**Mac/Linux:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install requests beautifulsoup4
```

---

## ▶️ How to Run

---

### 🟢 XML Pipeline

Compare two XML files:

```bash
python src/main.py data/normalized_xml/lebanon.xml data/normalized_xml/switzerland.xml custom
```

Available methods:

* `custom`
* `chawathe`
* `nj`

---

### 🔵 Wiki Pipeline

Compare two Wikipedia infobox files:

```bash
python src/wiki_main.py data/original_infobox_source/lebanon_infobox.wiki data/original_infobox_source/switzerland_infobox.wiki nj
```

---

### 🌍 Generate Wikipedia Infobox Files

```python
from wiki_source import fetch_page_wikitext, extract_infobox_block, save_infobox_block

page = fetch_page_wikitext("Albania")
infobox = extract_infobox_block(page)
save_infobox_block("Albania", infobox)
```

---

### 🌲 Visualize Trees

```bash
python src/visualize_trees.py xml data/normalized_xml/lebanon.xml data/normalized_xml/switzerland.xml chawathe
```

or

```bash
python src/visualize_trees.py wiki data/original_infobox_source/lebanon_infobox.wiki data/original_infobox_source/switzerland_infobox.wiki nj
```

---

## 🧠 Methodology

### 1. Preprocessing

* Parse XML or Wikipedia infobox
* Convert into tree structure

### 2. Tree Representation

Each node contains:

* label
* value
* children

### 3. Tree Edit Distance (TED)

Compute transformation cost between two trees.

Implemented algorithms:

* Custom recursive TED
* Chawathe
* Nierman–Jagadish

### 4. Edit Script

Operations:

* Insert
* Delete
* Update

### 5. Tree Patching

Apply operations to reconstruct target tree.

### 6. Postprocessing

Export results into:

* XML
* JSON
* Infobox text
* Reports

---

## 📊 Example Output

```text
Tree Edit Distance: 69
Similarity score: 0.5793

Inserts: 3
Deletes: 0
Updates: 63

Patch success: True
```

---

## 📈 Results Summary

| Method   | XML Performance | Wiki Performance |
| -------- | --------------- | ---------------- |
| Custom   | ✅ Consistent    | ⚠️ Less robust   |
| Chawathe | ✅ Strong        | ✅ Strong         |
| NJ       | ✅ Strong        | ⭐ Best           |

---

## 🎯 Design Choices

### Text Representation

* Used **single text node per value**
* Simpler and faster

### Dual Pipeline

* XML → controlled environment
* Wiki → real-world data

### Multiple TED Algorithms

* Enables comparison
* Improves robustness

---

## 🧪 Validation

* XML pipeline: all methods produce consistent results
* Wiki pipeline: NJ and Chawathe perform best
* Patch success validates correctness

---

## 🔮 Future Work

* Tokenized node representation
* Semantic tree abstraction
* Improved visualization
* Performance optimization

---

## 📚 References

* Chawathe, S. S. – Tree comparison algorithms
* Nierman, A., Jagadish, H. V. – XML similarity
* IDPA Course Material

---

## 👨‍💻 Authors

* Abbas Abdallah-Hasan Bazzi

---

## 📌 Notes

* Best method for demo:

  * XML → `custom`
  * Wiki → `nj`

* Ensure internet connection when fetching Wikipedia data

---

## ⭐ Conclusion

This project successfully implements a full pipeline for comparing and transforming Wikipedia infoboxes using tree-based techniques. It demonstrates the effectiveness of TED algorithms, especially literature-based approaches, in handling semi-structured data.

---
