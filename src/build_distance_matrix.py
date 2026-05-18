"""
CLI to build and cache the pairwise TED distance matrix.

Usage:
  python src/build_distance_matrix.py [--method nj] [--quick K] [--force]

Examples:
  python src/build_distance_matrix.py                   # full matrix, NJ method
  python src/build_distance_matrix.py --quick 20        # quick mode: top 20 countries
  python src/build_distance_matrix.py --method custom   # use custom TED
  python src/build_distance_matrix.py --force           # rebuild even if cache exists
"""
from __future__ import annotations

import argparse
import sys
import time


def _progress_bar(done: int, total: int, width: int = 40) -> str:
    pct = done / total if total > 0 else 1.0
    filled = int(pct * width)
    bar = "=" * filled + "-" * (width - filled)
    return f"[{bar}] {done}/{total} ({pct:.1%})"


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def _show_sample_pairs(
    countries: list[str],
    matrix: list[list[int]],
    n: int = 5,
) -> None:
    pairs: list[tuple[int, str, str]] = []
    for i in range(len(countries)):
        for j in range(i + 1, len(countries)):
            pairs.append((matrix[i][j], countries[i], countries[j]))

    pairs.sort(key=lambda x: x[0])

    print(f"\n  Closest {n} pairs:")
    for dist, a, b in pairs[:n]:
        print(f"    {a} <-> {b}  (distance={dist})")

    print(f"\n  Farthest {n} pairs:")
    for dist, a, b in pairs[-n:]:
        print(f"    {a} <-> {b}  (distance={dist})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and cache the pairwise TED distance matrix.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--method",
        choices=["custom", "chawathe", "nj"],
        default="nj",
        help="TED algorithm (default: nj)",
    )
    parser.add_argument(
        "--quick",
        metavar="K",
        type=int,
        default=None,
        help="Quick mode: use only the first K countries (alphabetical)",
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Apply full semantic preprocessing (slower but semantically richer trees)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if a cache file already exists",
    )
    args = parser.parse_args()

    from distance_matrix import (
        cache_path,
        compute_distance_matrix,
        get_xml_files,
        load_matrix,
        load_trees,
        save_matrix,
    )

    method: str = args.method
    top_k: int | None = args.quick
    preprocess: bool = args.preprocess
    path = cache_path(method, top_k, preprocess=preprocess)

    # Check existing cache
    if not args.force and path.exists():
        existing = load_matrix(method, top_k)
        if existing:
            cached_countries, _ = existing
            n = len(cached_countries)
            pairs = n * (n - 1) // 2
            print(f"Cache already exists: {path}")
            print(f"  {n} countries | {pairs} pairs | method={method}")
            print("Use --force to rebuild.")
            return

    xml_files = get_xml_files(top_k)
    n_countries = len(xml_files)
    total_pairs = n_countries * (n_countries - 1) // 2
    mode_label = f"top {n_countries}" if top_k else f"all {n_countries}"

    print(f"Building distance matrix")
    print(f"  method    : {method}")
    print(f"  trees     : {'preprocessed' if args.preprocess else 'raw'}")
    print(f"  countries : {mode_label}")
    print(f"  pairs     : {total_pairs}")
    print()

    # Phase 1: load trees
    print(f"Loading {n_countries} trees...", end=" ", flush=True)
    t0 = time.monotonic()
    trees = load_trees(xml_files, preprocess=preprocess)
    load_time = time.monotonic() - t0
    print(f"done ({load_time:.1f}s)")

    # Phase 2: compute pairwise distances with live progress bar
    last_print: list[float] = [0.0]
    t_compute_start: list[float] = [0.0]

    def progress_cb(done: int, total: int) -> None:
        now = time.monotonic()
        if done == 1:
            t_compute_start[0] = now
        if now - last_print[0] < 0.25 and done < total:
            return
        last_print[0] = now

        elapsed = now - t_compute_start[0]
        rate = done / elapsed if elapsed > 1e-6 else 0.0
        remaining = (total - done) / rate if rate > 0 else 0.0

        bar = _progress_bar(done, total)
        if done >= total:
            eta_str = f"done in {_fmt_time(elapsed)}"
        elif rate > 0:
            eta_str = f"ETA: {_fmt_time(remaining)}"
        else:
            eta_str = "estimating..."

        sys.stdout.write(f"\rComputing pairs: {bar} | {eta_str}   ")
        sys.stdout.flush()

    t_build_start = time.monotonic()
    countries, matrix = compute_distance_matrix(trees, method=method, progress_cb=progress_cb)
    print()  # end the progress-bar line

    # Phase 3: save
    out_path = save_matrix(countries, matrix, method=method, top_k=top_k, preprocess=preprocess)
    total_time = time.monotonic() - t_build_start

    print(f"\nSaved -> {out_path}")
    print(f"Total compute time: {_fmt_time(total_time)}")

    _show_sample_pairs(countries, matrix)


if __name__ == "__main__":
    main()
