import os
import sys
from parser import parse_xml_file
from preprocess import preprocess_tree
from utils import count_nodes, subtree_size, print_edit_script, trees_equal
from ted import ted_with_ops
from diff import save_edit_script, load_edit_script
from patch import apply_edit_script
from postprocess import save_tree_as_xml, save_tree_as_json, save_tree_as_wiki_infobox


def main() -> None:
    print("Program started.")

    if len(sys.argv) != 3:
        print("Usage: python src/main.py <file1.xml> <file2.xml>")
        print("Received arguments:", sys.argv)
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

    tree1 = preprocess_tree(parse_xml_file(file1))
    tree2 = preprocess_tree(parse_xml_file(file2))

    distance, ops = ted_with_ops(tree1, tree2, "/country[1]")

    max_size = max(subtree_size(tree1), subtree_size(tree2))
    similarity = 1 - (distance / max_size)
    similarity = max(0.0, similarity)

    print("Tree 1 nodes:", count_nodes(tree1))
    print("Tree 2 nodes:", count_nodes(tree2))
    print("Tree Edit Distance:", distance)
    print("Similarity score:", round(similarity, 4))

    print("\nEdit Script:\n")
    print_edit_script(ops)

    save_edit_script(ops, "data/output/edit_script.json")
    loaded_ops = load_edit_script("data/output/edit_script.json")
    patched_tree = apply_edit_script(tree1, loaded_ops)

    print("\nPatched tree equals Tree 2:", trees_equal(patched_tree, tree2))

    save_tree_as_xml(tree1, "data/output/tree1_normalized.xml")
    save_tree_as_xml(tree2, "data/output/tree2_normalized.xml")
    save_tree_as_xml(patched_tree, "data/output/patched_tree.xml")

    save_tree_as_json(tree1, "data/output/tree1_normalized.json")
    save_tree_as_json(tree2, "data/output/tree2_normalized.json")
    save_tree_as_json(patched_tree, "data/output/patched_tree.json")

    save_tree_as_wiki_infobox(tree1, "data/output/tree1_infobox.txt")
    save_tree_as_wiki_infobox(tree2, "data/output/tree2_infobox.txt")
    save_tree_as_wiki_infobox(patched_tree, "data/output/patched_infobox.txt")

    print("Saved normalized Tree 1 XML to data/output/tree1_normalized.xml")
    print("Saved normalized Tree 2 XML to data/output/tree2_normalized.xml")
    print("Saved patched tree XML to data/output/patched_tree.xml")

    print("Saved normalized Tree 1 JSON to data/output/tree1_normalized.json")
    print("Saved normalized Tree 2 JSON to data/output/tree2_normalized.json")
    print("Saved patched tree JSON to data/output/patched_tree.json")

    print("Saved Tree 1 infobox text to data/output/tree1_infobox.txt")
    print("Saved Tree 2 infobox text to data/output/tree2_infobox.txt")
    print("Saved patched infobox text to data/output/patched_infobox.txt")


if __name__ == "__main__":
    main()