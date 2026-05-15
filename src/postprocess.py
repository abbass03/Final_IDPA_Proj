import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from models import Node


def node_to_xml_element(node: Node) -> ET.Element:
    elem = ET.Element(node.label)

    text_children = [child for child in node.children if child.node_type == "text"]
    element_children = [child for child in node.children if child.node_type == "element"]
    attribute_children = [child for child in node.children if child.node_type == "attribute"]

    for attr_node in attribute_children:
        if attr_node.children and attr_node.children[0].node_type == "text":
            elem.set(attr_node.label, attr_node.children[0].value or "")

    if text_children:
        elem.text = text_children[0].value or ""

    for child in element_children:
        elem.append(node_to_xml_element(child))

    return elem


def save_tree_as_xml(root: Node, file_path: str) -> None:
    pretty_xml = tree_to_pretty_xml(root)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)


def tree_to_pretty_xml(root: Node) -> str:
    xml_root = node_to_xml_element(root)
    rough_string = ET.tostring(xml_root, encoding="utf-8")
    return minidom.parseString(rough_string).toprettyxml(indent="    ")


def tree_to_dict(node: Node):
    text_children = [child for child in node.children if child.node_type == "text"]
    element_children = [child for child in node.children if child.node_type == "element"]

    if not element_children:
        if text_children:
            return text_children[0].value or ""
        return node.value if node.value is not None else ""

    result = {}

    if text_children:
        result["_text"] = text_children[0].value or ""

    for child in element_children:
        child_value = tree_to_dict(child)

        if child.label in result:
            if not isinstance(result[child.label], list):
                result[child.label] = [result[child.label]]
            result[child.label].append(child_value)
        else:
            result[child.label] = child_value

    return result


def save_tree_as_json(root: Node, file_path: str) -> None:
    data = {root.label: tree_to_dict(root)}
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def extract_text_value(node: Node) -> str:
    text_parts = []
    nested_parts = []
    element_children = [child for child in node.children if child.node_type == "element"]
    multiple_element_children = len(element_children) > 1

    for child in node.children:
        if child.node_type == "text" and child.value is not None:
            value = child.value.strip()
            if value:
                text_parts.append(value)
        elif child.node_type == "element":
            nested = extract_text_value(child)
            if not nested:
                continue

            has_element_children = any(grand.node_type == "element" for grand in child.children)
            if has_element_children or multiple_element_children:
                nested_parts.append(f"{child.label}: {nested}")
            else:
                nested_parts.append(nested)

    if nested_parts and text_parts:
        return "; ".join(text_parts + nested_parts).strip()
    if nested_parts:
        return "; ".join(nested_parts).strip()
    return " ".join(part.strip() for part in text_parts if part and part.strip()).strip()


def tree_to_wiki_infobox_text(root: Node, template_name: str = "Infobox country") -> str:
    lines = [f"{{{{{template_name}"]

    for child in root.children:
        if child.node_type != "element":
            continue

        value = extract_text_value(child)

        if not value:
            value = ""

        lines.append(f"| {child.label} = {value}")

    lines.append("}}")
    return "\n".join(lines)


def save_tree_as_wiki_infobox(root: Node, file_path: str, template_name: str = "Infobox country") -> None:
    text = tree_to_wiki_infobox_text(root, template_name=template_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

def build_comparison_report(
    file1: str,
    file2: str,
    n1: int,
    n2: int,
    distance: int,
    similarity: float,
    summary: dict,
    patch_success: bool,
    patch_difference: str | None,
) -> str:
    lines = [
        "=== COUNTRY COMPARISON REPORT ===",
        "",
        f"File 1: {file1}",
        f"File 2: {file2}",
        "",
        "=== TREE STATS ===",
        f"Tree 1 nodes: {n1}",
        f"Tree 2 nodes: {n2}",
        "",
        "=== TED RESULT ===",
        f"Tree Edit Distance: {distance}",
        f"Similarity score: {round(similarity, 4)}",
        "",
        "=== EDIT SUMMARY ===",
        f"Inserts: {summary['insert']}",
        f"Deletes: {summary['delete']}",
        f"Updates: {summary['update']}",
        f"Total visible operations: {summary['total_visible']}",
        "",
        "=== PATCH RESULT ===",
        f"Patch success: {patch_success}",
    ]

    if patch_difference:
        lines.append(f"First difference: {patch_difference}")

    return "\n".join(lines) + "\n"


def save_comparison_report(
    file_path: str,
    file1: str,
    file2: str,
    n1: int,
    n2: int,
    distance: int,
    similarity: float,
    summary: dict,
    patch_success: bool,
    patch_difference: str | None,
) -> None:
    report = build_comparison_report(
        file1,
        file2,
        n1,
        n2,
        distance,
        similarity,
        summary,
        patch_success,
        patch_difference,
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report)
