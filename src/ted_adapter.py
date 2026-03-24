from __future__ import annotations

from models import Node
from lit_ted.tree import TreeNode as LitTreeNode

SEP = "::"


def encode_label(node: Node) -> str:
    """
    Encode node_type into the label so the literature TED algorithms
    still distinguish structure kinds.
    """
    return f"{node.node_type}{SEP}{node.label}"


def decode_label(label: str) -> tuple[str, str]:
    if SEP not in label:
        return "element", label
    node_type, pure_label = label.split(SEP, 1)
    return node_type, pure_label


def node_to_lit(node: Node) -> LitTreeNode:
    return LitTreeNode(
        label=encode_label(node),
        value=node.value,
        children=[node_to_lit(child) for child in node.children],
    )


def lit_to_node(node: LitTreeNode) -> Node:
    node_type, label = decode_label(node.label)
    return Node(
        label=label,
        node_type=node_type,
        value=node.value,
        children=[lit_to_node(child) for child in node.children],
    )