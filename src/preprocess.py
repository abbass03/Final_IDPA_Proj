import re
from models import Node


def normalize_label(label: str) -> str:
    label = label.strip().lower()
    label = label.replace(" ", "_").replace("-", "_")
    label = re.sub(r"[^a-z0-9_#]", "", label)
    label = re.sub(r"_+", "_", label)
    return label


def tokenize_text(text: str) -> list[str]:
    # split camelCase / PascalCase
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # replace punctuation with spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    return text.split()


def normalize_text(text: str) -> str:
    tokens = tokenize_text(text)
    return " ".join(tokens)


def preprocess_tree(node: Node) -> Node:
    node.label = normalize_label(node.label)

    if node.node_type == "text" and node.value is not None:
        node.value = normalize_text(node.value)

    for child in node.children:
        preprocess_tree(child)

    return node