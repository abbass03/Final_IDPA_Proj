from pathlib import Path

from wiki_parser import load_infobox_tree
from ted import ted_with_ops
from patch import apply_edit_script
from utils import trees_equal, first_tree_difference

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def count_nodes(node):
    return 1 + sum(count_nodes(child) for child in node.children)


def similarity_score(distance, n1, n2):
    denom = max(n1 + n2, 1)
    return 1.0 - (distance / denom)


def resolve_infobox_path(filename: str) -> Path:
    candidates = [
        DATA_DIR / "original_infobox_source" / filename,
        DATA_DIR / "output" / filename,
        DATA_DIR / "raw_wikitext" / filename,
        DATA_DIR / filename,
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Could not find {filename}. Checked:\n" +
        "\n".join(str(p) for p in candidates)
    )
    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Could not find {filename}. Checked:\n" +
        "\n".join(str(p) for p in candidates)
    )


def evaluate_pair(name1, file1, name2, file2):
    path1 = resolve_infobox_path(file1)
    path2 = resolve_infobox_path(file2)

    tree1 = load_infobox_tree(str(path1))
    tree2 = load_infobox_tree(str(path2))

    n1 = count_nodes(tree1)
    n2 = count_nodes(tree2)

    distance, ops = ted_with_ops(tree1, tree2, f"/{tree1.label}[1]")
    patched = apply_edit_script(tree1, ops)
    success = trees_equal(patched, tree2)
    difference = None if success else first_tree_difference(patched, tree2)

    sim = similarity_score(distance, n1, n2)

    return {
    "source": name1,
    "target": name2,
    "nodes_source": n1,
    "nodes_target": n2,
    "ted": distance,
    "similarity": round(sim, 4),
    "patch_success": success,
    "difference": difference,
}

def print_results(results):
    headers = [
        "source",
        "target",
        "nodes_source",
        "nodes_target",
        "ted",
        "similarity",
        "patch_success",
    ]

    row_format = "{:<12} {:<12} {:<13} {:<13} {:<8} {:<12} {:<14}"

    print(row_format.format(*headers))
    print("-" * 90)

    for r in results:
        print(row_format.format(
            str(r["source"]),
            str(r["target"]),
            str(r["nodes_source"]),
            str(r["nodes_target"]),
            str(r["ted"]),
            str(r["similarity"]),
            str(r["patch_success"]),
        ))


if __name__ == "__main__":
    pairs = [
    ("Lebanon", "lebanon_infobox.wiki", "Switzerland", "switzerland_infobox.wiki"),
    ("France", "france_infobox.wiki", "Germany", "germany_infobox.wiki"),
    ("Germany", "germany_infobox.wiki", "Japan", "japan_infobox.wiki"),
    ("Japan", "japan_infobox.wiki", "France", "france_infobox.wiki"),
]

    results = []
    for name1, file1, name2, file2 in pairs:
        try:
            result = evaluate_pair(name1, file1, name2, file2)
            results.append(result)
        except Exception as e:
            results.append({
                "source": name1,
                "target": name2,
                "nodes_source": "-",
                "nodes_target": "-",
                "ted": f"ERROR: {e}",
                "similarity": "-",
                "patch_success": "-",
            })

    print_results(results)