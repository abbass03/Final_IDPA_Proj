from __future__ import annotations

import re

from models import Node
from semantic_values import (
    classify_token,
    normalize_numeric_token,
    normalize_surface_text,
    normalize_text_value,
    parse_date_components,
    parse_measurement,
    tokenize_text,
)


def normalize_label(label: str) -> str:
    label = label.strip().lower()
    label = label.replace(" ", "_").replace("-", "_")
    label = re.sub(r"[^a-z0-9_#]", "", label)
    label = re.sub(r"_+", "_", label)
    return label


def build_text_child(label: str, value: str) -> Node:
    parent = Node(label=label, node_type="element")
    parent.add_child(Node(label="#text", node_type="text", value=value))
    return parent


def should_dissect_text(text: str, tokens: list[str]) -> bool:
    if parse_date_components(text) is not None:
        return True
    if parse_measurement(text) is not None:
        return True
    if len(tokens) > 1:
        return True
    return any(classify_token(token) != "word_token" for token in tokens)


def build_date_analysis(text: str) -> Node | None:
    parts = parse_date_components(text)
    if parts is None:
        return None

    date_node = Node(label="parsed_date", node_type="element")
    for key in ("year", "month", "day"):
        if key in parts:
            date_node.add_child(build_text_child(key, parts[key]))
    return date_node


def build_measurement_analysis(text: str) -> Node | None:
    parts = parse_measurement(text)
    if parts is None:
        return None

    measurement_node = Node(label="parsed_measurement", node_type="element")
    for key in ("currency", "number", "unit"):
        if key in parts:
            measurement_node.add_child(build_text_child(key, parts[key]))
    return measurement_node


def build_token_analysis(text: str) -> Node | None:
    tokens = tokenize_text(text)
    if not tokens or not should_dissect_text(text, tokens):
        return None

    token_root = Node(label="tokenized_value", node_type="element")

    for token in tokens:
        kind = classify_token(token)
        normalized = normalize_numeric_token(token) if kind == "number_token" else normalize_surface_text(token)
        token_root.add_child(build_text_child(kind, normalized.lower() if kind != "number_token" else normalized))

    return token_root


def normalize_text(text: str) -> str:
    return normalize_text_value(text)


def preprocess_tree(node: Node, analyze_text: bool = True) -> Node:
    node.label = normalize_label(node.label)

    if node.node_type == "text" and node.value is not None:
        normalized_text = normalize_text(node.value)
        node.value = normalized_text

        if analyze_text:
            analysis_children = []
            date_analysis = build_date_analysis(normalized_text)
            if date_analysis is not None:
                analysis_children.append(date_analysis)

            measurement_analysis = build_measurement_analysis(normalized_text)
            if measurement_analysis is not None:
                analysis_children.append(measurement_analysis)

            token_analysis = build_token_analysis(normalized_text)
            if token_analysis is not None:
                analysis_children.append(token_analysis)

            node.children = analysis_children

    for child in node.children:
        preprocess_tree(child, analyze_text=analyze_text and node.node_type != "text")

    return node
