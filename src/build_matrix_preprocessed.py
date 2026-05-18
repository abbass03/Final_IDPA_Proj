"""
Build a full 193-country TED distance matrix using preprocessed trees.

Phase 1  — Preprocess every tree and cache it as a JSON dict to
           data/preprocessed_trees/{country}.json

Phase 2  — Compute all 18 528 pairwise distances in parallel using
           multiprocessing.Pool (one worker per CPU core).
           Progress is saved every 500 pairs so the run is resumable.

Usage:
    python src/build_matrix_preprocessed.py --phase 1
    python src/build_matrix_preprocessed.py --phase 2
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths  (this script lives in src/, so parent is project root)
# ---------------------------------------------------------------------------
_SRC  = Path(__file__).resolve().parent
_ROOT = _SRC.parent
_XML_DIR    = _ROOT / "data" / "normalized_xml"
_CACHE_DIR  = _ROOT / "data" / "preprocessed_trees"
_MATRIX_OUT = _ROOT / "data" / "distance_matrix_preprocessed_chawathe.json"

# Make src/ importable for worker processes (spawn re-imports this module)
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s:02d}s"
    return f"{m}m {s:02d}s" if m else f"{s}s"


def _count_nodes_dict(d: dict) -> int:
    """Count nodes in a Node.to_dict() structure without importing Node."""
    return 1 + sum(_count_nodes_dict(c) for c in d.get("children", []))


def _sorted_countries() -> list[str]:
    return [p.stem for p in sorted(_XML_DIR.glob("*.xml"))]


# ---------------------------------------------------------------------------
# Phase 1: preprocess and cache
# ---------------------------------------------------------------------------

def run_phase1() -> list[str]:
    from parser import parse_xml_file
    from preprocess import preprocess_tree
    from utils import count_nodes

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    xml_files = sorted(_XML_DIR.glob("*.xml"))
    total = len(xml_files)
    total_nodes = 0
    skipped = 0

    print(f"Phase 1 — preprocessing {total} country trees")
    print(f"Output  : {_CACHE_DIR}\n")

    t0 = time.monotonic()

    for idx, xml_path in enumerate(xml_files, 1):
        country  = xml_path.stem
        out_path = _CACHE_DIR / f"{country}.json"

        if out_path.exists():
            d = json.loads(out_path.read_text(encoding="utf-8"))
            n = _count_nodes_dict(d)
            total_nodes += n
            skipped += 1
            print(f"  [{idx:3d}/{total}] {country:<40s} {n:5d} nodes  (cached)")
            continue

        tree = parse_xml_file(str(xml_path))
        preprocess_tree(tree)       # mutates in place
        n = count_nodes(tree)
        total_nodes += n

        out_path.write_text(
            json.dumps(tree.to_dict(), separators=(",", ":")),
            encoding="utf-8",
        )

        elapsed = time.monotonic() - t0
        print(f"  [{idx:3d}/{total}] {country:<40s} {n:5d} nodes  ({elapsed:.1f}s)")

    elapsed = time.monotonic() - t0
    countries = [p.stem for p in xml_files]

    print()
    print("=" * 60)
    print(f"Phase 1 complete")
    print(f"  Trees     : {total}  ({skipped} already cached, {total - skipped} freshly built)")
    print(f"  Total time: {_fmt_time(elapsed)}")
    print(f"  Avg nodes : {total_nodes // total:,}  (total {total_nodes:,})")
    print("=" * 60)

    return countries


# ---------------------------------------------------------------------------
# Phase 2: parallel distance computation
#
# Worker architecture: each worker process calls _worker_init once,
# which reads all preprocessed tree dicts from disk into a module-level
# dict.  Each pair task then only passes (i, j, name_i, name_j) — minimal
# IPC overhead.
# ---------------------------------------------------------------------------

_WORKER_TREES: dict[str, dict] | None = None


def _worker_init(cache_dir: str, countries: list[str]) -> None:
    """Runs once per worker process: loads all tree dicts from disk."""
    global _WORKER_TREES
    p = Path(cache_dir)
    _WORKER_TREES = {
        name: json.loads((p / f"{name}.json").read_text(encoding="utf-8"))
        for name in countries
    }


def _compute_pair(args: tuple[int, int, str, str]) -> tuple[int, int, int]:
    """Runs in a worker process for each (i, j) pair."""
    i, j, name_i, name_j = args
    from models import Node
    from ted import ted_distance_only

    tree_i = Node.from_dict(_WORKER_TREES[name_i])
    tree_j = Node.from_dict(_WORKER_TREES[name_j])
    dist = ted_distance_only(tree_i, tree_j, method="chawathe")
    return i, j, dist


# ---------------------------------------------------------------------------

def run_phase2(countries: list[str]) -> None:
    n = len(countries)
    total_pairs = n * (n - 1) // 2

    # ----- initialise or resume from partial matrix -------------------------
    matrix: list[list[int]] = [[-1] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 0

    already_done = 0

    if _MATRIX_OUT.exists():
        try:
            saved = json.loads(_MATRIX_OUT.read_text(encoding="utf-8"))
            if saved.get("countries") == countries:
                flat = saved["matrix"]
                for i in range(n):
                    for j in range(n):
                        matrix[i][j] = flat[i * n + j]
                already_done = sum(
                    1 for i in range(n) for j in range(i + 1, n)
                    if matrix[i][j] != -1
                )
                print(f"Resuming: {already_done}/{total_pairs} pairs already done.\n")
            else:
                print("Existing file has different country list — starting fresh.\n")
        except Exception as e:
            print(f"Could not load existing matrix ({e}) — starting fresh.\n")

    # ----- build list of remaining pairs ------------------------------------
    pairs = [
        (i, j, countries[i], countries[j])
        for i in range(n)
        for j in range(i + 1, n)
        if matrix[i][j] == -1
    ]
    remaining = len(pairs)

    if remaining == 0:
        print("All pairs already computed. Nothing to do.")
        return

    _PROGRESS_FILE = _ROOT / "data" / "matrix_build_progress.json"

    # ----- save helper ------------------------------------------------------
    def save_matrix(completed: int, elapsed: float) -> None:
        rate = completed / elapsed if elapsed > 1e-6 else 0.0
        eta  = (total_pairs - completed) / rate if rate > 0 else 0.0
        # progress sidecar — easy to poll without parsing the full matrix
        _PROGRESS_FILE.write_text(
            json.dumps({
                "completed": completed,
                "total": total_pairs,
                "pct": round(completed / total_pairs * 100, 2),
                "rate_per_s": round(rate, 3),
                "elapsed_s": round(elapsed, 1),
                "eta_s": round(eta, 1),
                "eta_human": _fmt_time(eta),
            }),
            encoding="utf-8",
        )
        _MATRIX_OUT.write_text(
            json.dumps(
                {
                    "method": "chawathe",
                    "preprocess": True,
                    "countries": countries,
                    "completed": completed,
                    "total": total_pairs,
                    "matrix": [matrix[i][j] for i in range(n) for j in range(n)],
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

    # ----- run --------------------------------------------------------------
    ncpu = multiprocessing.cpu_count()
    print(f"Phase 2 — {remaining} pairs remaining  ({already_done} already done)")
    print(f"  Workers : {ncpu} CPU cores")
    print(f"  Method  : chawathe (preprocessed trees)")
    print(f"  Output  : {_MATRIX_OUT}")
    print(f"  Saving  : every 500 pairs\n")

    completed = already_done
    last_saved = already_done
    t0 = time.monotonic()

    try:
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(
            processes=ncpu,
            initializer=_worker_init,
            initargs=(str(_CACHE_DIR), countries),
        ) as pool:
            for i_res, j_res, dist in pool.imap_unordered(
                _compute_pair, pairs, chunksize=1
            ):
                matrix[i_res][j_res] = dist
                matrix[j_res][i_res] = dist
                completed += 1
                elapsed = time.monotonic() - t0

                # print a line every 500 pairs (readable in log files)
                if completed - last_saved >= 500:
                    save_matrix(completed, elapsed)
                    last_saved = completed
                    rate = completed / elapsed if elapsed > 1e-6 else 0.0
                    eta  = (total_pairs - completed) / rate if rate > 0 else 0.0
                    print(
                        f"completed {completed}/{total_pairs} pairs"
                        f" ({completed / total_pairs:.1%})"
                        f" | {rate:.2f} pairs/s"
                        f" | ETA {_fmt_time(eta)}",
                        flush=True,
                    )

    except KeyboardInterrupt:
        print("\nInterrupted — saving progress...")
        save_matrix(completed, time.monotonic() - t0)
        print(f"Saved {completed}/{total_pairs} pairs to {_MATRIX_OUT}")
        return
    except Exception as exc:
        print(f"\nError: {exc}")
        print("Saving progress before exit...")
        save_matrix(completed, time.monotonic() - t0)
        raise

    # ----- final save -------------------------------------------------------
    save_matrix(completed, time.monotonic() - t0)
    elapsed = time.monotonic() - t0
    print(f"\nPhase 2 complete in {_fmt_time(elapsed)}")
    print(f"Matrix saved -> {_MATRIX_OUT}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=["1", "2"],
        required=True,
        help="Which phase to run",
    )
    args = parser.parse_args()

    if args.phase == "1":
        run_phase1()
        print()
        print("Review the node counts above.")
        print("When ready, run Phase 2 with:")
        print("  python src/build_matrix_preprocessed.py --phase 2")

    else:
        countries = _sorted_countries()
        if not (_CACHE_DIR / f"{countries[0]}.json").exists():
            print("ERROR: preprocessed_trees/ not found. Run Phase 1 first.")
            sys.exit(1)
        run_phase2(countries)
