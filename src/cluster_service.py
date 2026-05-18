"""
Clustering service: loads the preprocessed distance matrix, extracts
submatrices, runs algorithms, computes MDS 2-D projections and metrics.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent

_MATRIX_PATH = _ROOT / "data" / "distance_matrix_preprocessed_chawathe.json"
_XML_DIR = _ROOT / "data" / "normalized_xml"

# module-level cache — loaded once per server process
_cached_countries: list[str] | None = None
_cached_matrix: list[list[int]] | None = None

# Custom countries added at runtime (name → xml path)
_custom_country_paths: dict[str, Path] = {}
# Session-level on-the-fly distance cache: frozenset({a,b}) → dist
_otf_distances: dict[frozenset, int] = {}


def _ensure_loaded() -> tuple[list[str], list[list[int]]]:
    global _cached_countries, _cached_matrix
    if _cached_countries is None:
        raw = json.loads(_MATRIX_PATH.read_text(encoding="utf-8"))
        _cached_countries = raw["countries"]
        n = len(_cached_countries)
        flat = raw["matrix"]
        # stored as flat row-major array
        _cached_matrix = [[flat[i * n + j] for j in range(n)] for i in range(n)]
    return _cached_countries, _cached_matrix


def _load_tree(name: str):
    """Load and preprocess a country tree from its XML file."""
    import sys as _sys
    _sys.path.insert(0, str(_ROOT / "src"))
    from parser import parse_xml_file
    from preprocess import preprocess_tree

    if name in _custom_country_paths:
        xml_path = _custom_country_paths[name]
    else:
        xml_path = _XML_DIR / f"{name}.xml"
    return preprocess_tree(parse_xml_file(str(xml_path)))


def _otf_distance(a: str, b: str) -> int:
    """Compute TED distance on-the-fly (cached per session)."""
    key = frozenset({a, b})
    if key not in _otf_distances:
        import sys as _sys
        _sys.path.insert(0, str(_ROOT / "src"))
        from ted import ted_distance_only
        ta = _load_tree(a)
        tb = _load_tree(b)
        _otf_distances[key] = ted_distance_only(ta, tb, method="chawathe")
    return _otf_distances[key]


def register_custom_country(name: str, xml_path: Path) -> None:
    """Register a newly uploaded country so it appears in available_countries()."""
    _custom_country_paths[name] = xml_path


def available_countries() -> list[str]:
    countries, _ = _ensure_loaded()
    custom = [c for c in _custom_country_paths if c not in set(countries)]
    return countries + sorted(custom)


def extract_submatrix(selected: list[str]) -> list[list[int]]:
    all_countries, full = _ensure_loaded()
    idx = {c: i for i, c in enumerate(all_countries)}
    n = len(selected)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            ci, cj = selected[i], selected[j]
            if ci in idx and cj in idx:
                d = full[idx[ci]][idx[cj]]
            else:
                d = _otf_distance(ci, cj)
            matrix[i][j] = matrix[j][i] = d
    return matrix


# ---------------------------------------------------------------------------
# MDS (classical, 2-D)
# ---------------------------------------------------------------------------

def mds_2d(dist_matrix: list[list[int]]) -> list[list[float]]:
    """Classical MDS via numpy eigendecomposition. Falls back to circle layout."""
    try:
        import numpy as np
        n = len(dist_matrix)
        D = np.array(dist_matrix, dtype=float)
        D2 = D ** 2
        H = np.eye(n) - np.ones((n, n)) / n
        B = -0.5 * H @ D2 @ H
        vals, vecs = np.linalg.eigh(B)
        order = np.argsort(vals)[::-1]
        vals = np.maximum(vals[order[:2]], 0)
        vecs = vecs[:, order[:2]]
        coords = (vecs * np.sqrt(vals)).tolist()
        return coords
    except ImportError:
        n = len(dist_matrix)
        return [
            [math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)]
            for i in range(n)
        ]


# ---------------------------------------------------------------------------
# K-Means (Lloyd's on MDS 2-D coordinates, K-Means++ init)
# ---------------------------------------------------------------------------

def _kmeans(coords: list[list[float]], k: int, max_iter: int = 300, n_init: int = 10) -> list[int]:
    n, dim = len(coords), len(coords[0])

    def sq(a: list[float], b: list[float]) -> float:
        return sum((a[d] - b[d]) ** 2 for d in range(dim))

    best_labels: list[int] = [0] * n
    best_inertia = float("inf")

    for _ in range(n_init):
        # K-Means++ seeding
        centers = [list(random.choice(coords))]
        for _ in range(k - 1):
            dists = [min(sq(p, c) for c in centers) for p in coords]
            total = sum(dists)
            r = random.uniform(0, total) if total > 0 else 0.0
            cumsum = 0.0
            chosen = coords[-1]
            for p, d in zip(coords, dists):
                cumsum += d
                if cumsum >= r:
                    chosen = p
                    break
            centers.append(list(chosen))

        labels = [0] * n
        for _ in range(max_iter):
            new_labels = [min(range(k), key=lambda c, i=i: sq(coords[i], centers[c])) for i in range(n)]
            if new_labels == labels:
                break
            labels = new_labels
            for c in range(k):
                pts = [coords[i] for i in range(n) if labels[i] == c]
                if pts:
                    centers[c] = [sum(p[d] for p in pts) / len(pts) for d in range(dim)]

        inertia = sum(sq(coords[i], centers[labels[i]]) for i in range(n))
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels[:]

    return best_labels


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

def run_clustering(
    countries: list[str],
    matrix: list[list[int]],
    algorithm: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    from clustering import (
        agglomerative_clustering,
        dbscan_clustering,
        dunn_index,
        kmedoids_clustering,
        silhouette_score,
    )

    alg = algorithm.lower()
    result: dict[str, Any] = {}

    if alg == "ahc":
        k = int(params.get("n_clusters", 5))
        linkage = str(params.get("linkage", "average"))
        result = agglomerative_clustering(countries, matrix, n_clusters=k, linkage=linkage)

    elif alg == "kmedoids":
        k = int(params.get("k", 5))
        result = kmedoids_clustering(countries, matrix, k=k)

    elif alg == "kmeans":
        k = int(params.get("k", 5))
        coords = mds_2d(matrix)
        labels = _kmeans(coords, k)
        cluster_members: dict[int, list[str]] = {c: [] for c in range(k)}
        assignments: dict[str, int] = {}
        for i, cid in enumerate(labels):
            cluster_members[cid].append(countries[i])
            assignments[countries[i]] = cid
        result = {
            "algorithm": "kmeans",
            "n_clusters": k,
            "assignments": assignments,
            "cluster_members": cluster_members,
        }

    elif alg == "dbscan":
        eps = float(params.get("eps", 300))
        min_samples = int(params.get("min_samples", 2))
        result = dbscan_clustering(countries, matrix, eps=eps, min_samples=min_samples)

    else:
        raise ValueError(f"Unknown algorithm: {algorithm!r}")

    # Attach MDS coordinates, raw matrix, and ordered country list
    result["coords_2d"] = mds_2d(matrix)
    result["countries"] = countries
    result["matrix"] = matrix

    # Metrics (exclude DBSCAN noise points labeled -1)
    assignments_map: dict[str, int] = result.get("assignments", {})
    valid = [c for c in countries if assignments_map.get(c, -1) != -1]
    unique_ids = {assignments_map[c] for c in valid}
    if len(valid) >= 2 and len(unique_ids) >= 2:
        vi = [countries.index(c) for c in valid]
        vm = [[matrix[r][c] for c in vi] for r in vi]
        va = {c: assignments_map[c] for c in valid}
        sil, _ = silhouette_score(valid, vm, va)
        di = dunn_index(valid, vm, va)
        result["metrics"] = {"silhouette": round(sil, 4), "dunn": round(di, 4)}
    else:
        result["metrics"] = {"silhouette": None, "dunn": None}

    # JSON requires string keys
    result["cluster_members"] = {
        str(k): v for k, v in result.get("cluster_members", {}).items()
    }
    if "noise" not in result:
        result["noise"] = []

    return result
