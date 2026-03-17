# src/evaluate_xml_pipeline.py

from pathlib import Path

from parser import parse_xml_file
from preprocess import preprocess_tree
from ted import ted_with_ops
from patch import apply_edit_script
from utils import count_nodes, trees_equal


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def similarity_score(distance: int, n1: int, n2: int) -> float:
    denom = max(n1 + n2, 1)
    return 1.0 - (distance / denom)


def resolve_xml_path(filename: str) -> Path:
    candidates = [
        DATA_DIR / "raw_xml" / filename,
        DATA_DIR / "normalized_xml" / filename,
        DATA_DIR / "raw" / filename,
        DATA_DIR / filename,
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Could not find {filename}. Checked:\n" +
        "\n".join(str(p) for p in candidates)
    )


def load_preprocessed_xml_tree(file_name: str):
    path = resolve_xml_path(file_name)
    tree = parse_xml_file(str(path))
    tree = preprocess_tree(tree)
    return tree


def first_tree_difference(a, b, path="root"):
    if a.label != b.label:
        return f"{path}: label mismatch ({a.label} != {b.label})"

    if a.node_type != b.node_type:
        return f"{path}: node_type mismatch ({a.node_type} != {b.node_type})"

    if (a.value or "") != (b.value or ""):
        return f"{path}: value mismatch ({a.value!r} != {b.value!r})"

    if len(a.children) != len(b.children):
        return f"{path}: child count mismatch ({len(a.children)} != {len(b.children)})"

    for i, (ca, cb) in enumerate(zip(a.children, b.children), start=1):
        diff = first_tree_difference(ca, cb, f"{path}/{ca.label}[{i}]")
        if diff:
            return diff

    return None


def evaluate_pair(name1: str, file1: str, name2: str, file2: str) -> dict:
    tree1 = load_preprocessed_xml_tree(file1)
    tree2 = load_preprocessed_xml_tree(file2)

    n1 = count_nodes(tree1)
    n2 = count_nodes(tree2)

    root_path = f"/{tree1.label}[1]"
    distance, ops = ted_with_ops(tree1, tree2, root_path)

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


def print_results(results: list[dict]) -> None:
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

        if r.get("difference"):
            print("  first_difference:", r["difference"])


if __name__ == "__main__":
    pairs = [
        ("Lebanon", "lebanon.xml", "Switzerland", "switzerland.xml"),
        ("Switzerland", "switzerland.xml", "Lebanon", "lebanon.xml"),
        ("France", "france.xml", "Germany", "germany.xml"),
        ("Germany", "germany.xml", "Japan", "japan.xml"),
        ("Japan", "japan.xml", "France", "france.xml"),
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
                "difference": None,
            })

    print_results(results)