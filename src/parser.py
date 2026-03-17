import xml.etree.ElementTree as ET
from models import Node


def xml_element_to_node(elem: ET.Element) -> Node:
    # element node
    node = Node(label=elem.tag, node_type="element")

    # attributes first, sorted by name
    for attr_name in sorted(elem.attrib.keys()):
        attr_node = Node(label=attr_name, node_type="attribute")
        attr_value = elem.attrib[attr_name].strip()
        if attr_value:
            attr_node.add_child(Node(label="#text", node_type="text", value=attr_value))
        node.add_child(attr_node)

    # text content
    if elem.text and elem.text.strip():
        text_value = elem.text.strip()
        node.add_child(Node(label="#text", node_type="text", value=text_value))

    # child elements in original order
    for child in elem:
        node.add_child(xml_element_to_node(child))

        # optional: tail text after child
        if child.tail and child.tail.strip():
            tail_value = child.tail.strip()
            node.add_child(Node(label="#text", node_type="text", value=tail_value))

    return node


def parse_xml_file(file_path: str) -> Node:
    tree = ET.parse(file_path)
    root = tree.getroot()
    return xml_element_to_node(root)