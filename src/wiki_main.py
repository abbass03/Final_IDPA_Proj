import os
import sys

from wiki_parser import load_infobox_tree
from ted import ted_with_ops
from diff import save_edit_script, load_edit_script
from patch import apply_edit_script
from wiki_serializer import save_infobox_wikitext
from utils import subtree_size, count_nodes, print_edit_script, trees_equal


def main() -> None:
    print("Wiki pipeline started.")

    if len(sys.argv) != 3:
        print("Usage: python src/wiki_main.py <file1.wiki> <file2.wiki>")
        return

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    print("File 1:", file1)
    print("File 2:", file2)

    if not os.path.exists(file1):
        print(f"Error: file not found -> {file1}")
        return

    if not os.path.exists(file2):
        print(f"Error: file not found -> {file2}")
        return

    tree1 = load_infobox_tree(file1)
    tree2 = load_infobox_tree(file2)

    distance, ops = ted_with_ops(tree1, tree2, f"/{tree1.label}[1]")

    max_size = max(subtree_size(tree1), subtree_size(tree2))
    similarity = 1 - (distance / max_size)
    similarity = max(0.0, similarity)

    print("Tree 1 nodes:", count_nodes(tree1))
    print("Tree 2 nodes:", count_nodes(tree2))
    print("Tree Edit Distance:", distance)
    print("Similarity score:", round(similarity, 4))

    print("\nEdit Script:\n")
    print_edit_script(ops)

    os.makedirs("data/output", exist_ok=True)

    save_edit_script(ops, "data/output/wiki_edit_script.json")
    loaded_ops = load_edit_script("data/output/wiki_edit_script.json")

    patched_tree = apply_edit_script(tree1, loaded_ops)

    print("\nPatched tree equals Tree 2:", trees_equal(patched_tree, tree2))

    save_infobox_wikitext(tree1, "data/output/tree1_infobox.wiki")
    save_infobox_wikitext(tree2, "data/output/tree2_infobox.wiki")
    save_infobox_wikitext(patched_tree, "data/output/patched_infobox.wiki")

    print("Saved Tree 1 infobox to data/output/tree1_infobox.wiki")
    print("Saved Tree 2 infobox to data/output/tree2_infobox.wiki")
    print("Saved patched infobox to data/output/patched_infobox.wiki")


if __name__ == "__main__":
    main()