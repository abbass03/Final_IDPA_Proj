from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from models import Node
from parser import parse_xml_file
from preprocess import preprocess_tree
from ted import ted_distance_only

_SRC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SRC_DIR.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_XML_DIR = _DATA_DIR / "normalized_xml"


def get_xml_files(top_k: int | None = None) -> list[Path]:
    files = sorted(_XML_DIR.glob("*.xml"))
    if top_k is not None:
        files = files[:top_k]
    return files


def load_trees(xml_files: list[Path], preprocess: bool = False) -> list[tuple[str, Node]]:
    result = []
    for f in xml_files:
        tree = parse_xml_file(str(f))
        if preprocess:
            tree = preprocess_tree(tree)
        result.append((f.stem, tree))
    return result


def compute_distance_matrix(
    trees: list[tuple[str, Node]],
    method: str = "nj",
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[list[str], list[list[int]]]:
    n = len(trees)
    countries = [name for name, _ in trees]
    matrix: list[list[int]] = [[0] * n for _ in range(n)]

    total_pairs = n * (n - 1) // 2
    done = 0

    for i in range(n):
        _, tree_i = trees[i]
        for j in range(i + 1, n):
            _, tree_j = trees[j]
            distance = ted_distance_only(tree_i, tree_j, method=method)
            matrix[i][j] = distance
            matrix[j][i] = distance
            done += 1
            if progress_cb is not None:
                progress_cb(done, total_pairs)

    return countries, matrix


def cache_path(method: str, top_k: int | None = None, preprocess: bool = False) -> Path:
    name = f"distance_matrix_{method}"
    if preprocess:
        name += "_pre"
    if top_k is not None:
        name += f"_top{top_k}"
    return _DATA_DIR / f"{name}.json"


def save_matrix(
    countries: list[str],
    matrix: list[list[int]],
    method: str,
    top_k: int | None = None,
    preprocess: bool = False,
) -> Path:
    path = cache_path(method, top_k, preprocess=preprocess)
    payload = {
        "method": method,
        "top_k": top_k,
        "preprocess": preprocess,
        "countries": countries,
        "matrix": matrix,
    }
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return path


def load_matrix(
    method: str,
    top_k: int | None = None,
    preprocess: bool = False,
) -> tuple[list[str], list[list[int]]] | None:
    path = cache_path(method, top_k, preprocess=preprocess)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["countries"], payload["matrix"]


def build_and_save(
    method: str = "nj",
    top_k: int | None = None,
    preprocess: bool = False,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[list[str], list[list[int]]]:
    """Load trees, compute all pairwise distances, save to cache, and return result."""
    xml_files = get_xml_files(top_k)
    trees = load_trees(xml_files, preprocess=preprocess)
    countries, matrix = compute_distance_matrix(trees, method=method, progress_cb=progress_cb)
    save_matrix(countries, matrix, method=method, top_k=top_k, preprocess=preprocess)
    return countries, matrix
