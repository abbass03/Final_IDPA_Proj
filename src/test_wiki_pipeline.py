from wiki_parser import parse_infobox_to_tree
from wiki_serializer import tree_to_infobox_wikitext
from ted import ted_with_ops
from patch import apply_edit_script
from utils import trees_equal


def test_round_trip_parse_serialize_parse():
    infobox = """{{Infobox country
| name = Lebanon
| capital = [[Beirut]]
| languages = [[Arabic]]<br>[[French]]
| flag = {{flag|Lebanon}}
}}"""

    tree1 = parse_infobox_to_tree(infobox)
    text2 = tree_to_infobox_wikitext(tree1)
    tree2 = parse_infobox_to_tree(text2)

    assert trees_equal(tree1, tree2), "Round-trip parse/serialize/parse should preserve tree structure"


def test_identical_trees_have_zero_distance():
    infobox = """{{Infobox country
| name = Lebanon
| capital = [[Beirut]]
}}"""

    tree1 = parse_infobox_to_tree(infobox)
    tree2 = parse_infobox_to_tree(infobox)

    distance, ops = ted_with_ops(tree1, tree2, f"/{tree1.label}[1]")
    visible_ops = [op for op in ops if op.op != "match"]

    assert distance == 0, "Identical trees should have TED = 0"
    assert len(visible_ops) == 0, "Identical trees should produce no visible edit operations"


def test_patch_reconstructs_target_tree():
    infobox1 = """{{Infobox country
| name = Lebanon
| capital = [[Beirut]]
| languages = [[Arabic]]
}}"""

    infobox2 = """{{Infobox country
| name = Lebanon
| capital = [[Beirut]]
| languages = [[Arabic]]<br>[[French]]
| flag = {{flag|Lebanon}}
}}"""

    tree1 = parse_infobox_to_tree(infobox1)
    tree2 = parse_infobox_to_tree(infobox2)

    distance, ops = ted_with_ops(tree1, tree2, f"/{tree1.label}[1]")
    visible_ops = [op for op in ops if op.op != "match"]

    assert distance > 0, "Different trees should have TED > 0"
    assert len(visible_ops) > 0, "Different trees should produce visible edit operations"

    patched = apply_edit_script(tree1, ops)

    assert trees_equal(patched, tree2), "Applying edit script should reconstruct the target tree"

    


def test_link_structure_is_preserved():
    infobox = """{{Infobox country
| capital = [[Beirut|Capital of Lebanon]]
}}"""

    tree = parse_infobox_to_tree(infobox)
    capital_node = tree.children[0]

    assert capital_node.label == "capital"
    assert len(capital_node.children) == 1

    link_node = capital_node.children[0]
    assert link_node.label == "link"
    assert len(link_node.children) >= 1

    serialized = tree_to_infobox_wikitext(tree)
    assert "[[Beirut|Capital of Lebanon]]" in serialized


def test_template_structure_is_preserved():
    infobox = """{{Infobox country
| flag = {{flag|Lebanon}}
}}"""

    tree = parse_infobox_to_tree(infobox)
    flag_node = tree.children[0]

    assert flag_node.label == "flag"
    assert len(flag_node.children) == 1

    template_node = flag_node.children[0]
    assert template_node.label == "template:flag"

    serialized = tree_to_infobox_wikitext(tree)
    assert "{{flag|Lebanon}}" in serialized


if __name__ == "__main__":
    test_round_trip_parse_serialize_parse()
    test_identical_trees_have_zero_distance()
    test_patch_reconstructs_target_tree()
    test_link_structure_is_preserved()
    test_template_structure_is_preserved()
    print("All wiki pipeline tests passed.")