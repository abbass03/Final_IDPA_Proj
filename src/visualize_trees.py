from __future__ import annotations

import sys
from pathlib import Path

from parser import parse_xml_file
from preprocess import preprocess_tree
from wiki_parser import load_infobox_tree
from ted import ted_with_ops, patch_with_ops


def save_text(path: str, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def xml_mode(file1: str, file2: str, method: str) -> None:
    tree1 = preprocess_tree(parse_xml_file(file1))
    tree2 = preprocess_tree(parse_xml_file(file2))

    distance, ops = ted_with_ops(tree1, tree2, "/country[1]", method=method)
    patched_tree = patch_with_ops(tree1, ops, method=method)

    from utils import format_tree

    print("\n=== SOURCE TREE ===\n")
    print(format_tree(tree1))

    print("\n=== TARGET TREE ===\n")
    print(format_tree(tree2))

    print("\n=== PATCHED TREE ===\n")
    print(format_tree(patched_tree))    

    save_text("data/output/source_tree.txt",format_tree(tree1))
    save_text("data/output/target_tree.txt", format_tree(tree2))
    save_text("data/output/patched_tree.txt", format_tree(patched_tree))

    print("\nSaved:")
    print("data/output/source_tree.txt")
    print("data/output/target_tree.txt")
    print("data/output/patched_tree.txt")
    print(f"\nTED distance: {distance}")


def wiki_mode(file1: str, file2: str, method: str) -> None:
    tree1 = load_infobox_tree(file1)
    tree2 = load_infobox_tree(file2)

    distance, ops = ted_with_ops(tree1, tree2, f"/{tree1.label}[1]", method=method)
    patched_tree = patch_with_ops(tree1, ops, method=method)

    from utils import format_tree

    print("\n=== SOURCE TREE ===\n")
    print(format_tree(tree1))

    print("\n=== TARGET TREE ===\n")
    print(format_tree(tree2))

    print("\n=== PATCHED TREE ===\n")
    print(format_tree(patched_tree))


    save_text("data/output/source_tree.txt", format_tree(tree1))
    save_text("data/output/target_tree.txt", format_tree(tree2))
    save_text("data/output/patched_tree.txt", format_tree(patched_tree))

    print("\nSaved:")
    print("data/output/source_tree.txt")
    print("data/output/target_tree.txt")
    print("data/output/patched_tree.txt")
    print(f"\nTED distance: {distance}")


def main() -> None:
    if len(sys.argv) not in (4, 5):
        print("Usage:")
        print("  python src/visualize_trees.py xml <file1.xml> <file2.xml> [custom|chawathe|nj]")
        print("  python src/visualize_trees.py wiki <file1.wiki> <file2.wiki> [custom|chawathe|nj]")
        return

    mode = sys.argv[1].lower()
    file1 = sys.argv[2]
    file2 = sys.argv[3]
    method = sys.argv[4].lower() if len(sys.argv) == 5 else "custom"

    if mode == "xml":
        xml_mode(file1, file2, method)
    elif mode == "wiki":
        wiki_mode(file1, file2, method)
    else:
        print("Mode must be 'xml' or 'wiki'.")



if __name__ == "__main__":
    main()