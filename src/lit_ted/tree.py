from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class TreeNode:
    label: str
    value: Optional[str] = None
    children: List["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "children": [child.to_dict() for child in self.children],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TreeNode":
        return TreeNode(
            label=data["label"],
            value=data.get("value"),
            children=[TreeNode.from_dict(c) for c in data.get("children", [])],
        )


def _normalize_scalar(value: Optional[str]) -> Optional[Union[str, float, int]]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _node_is_empty(node: TreeNode) -> bool:
    if node.children:
        return all(_node_is_empty(c) for c in node.children)
    return node.value is None or (
        isinstance(node.value, str) and not node.value.strip()
    )


def tree_similarity(t1: TreeNode, t2: TreeNode) -> float:
    matches = 0
    total = 0

    def _unmatched_subtree(node: TreeNode) -> None:
        nonlocal matches, total
        if not _node_is_empty(node):
            total += 2
        for ch in node.children:
            _unmatched_subtree(ch)

    def _score(n1: TreeNode, n2: TreeNode) -> None:
        nonlocal matches, total

        total += 1
        if n1.label == n2.label:
            matches += 1

        total += 1
        v1 = n1.value if n1.value is not None else ""
        v2 = n2.value if n2.value is not None else ""
        if v1 == v2:
            matches += 1

        from collections import defaultdict, deque
        by_label = defaultdict(deque)
        for c in n2.children:
            by_label[c.label].append(c)

        for c1 in n1.children:
            q = by_label[c1.label]
            if q:
                _score(c1, q.popleft())
            else:
                _unmatched_subtree(c1)

        for q in by_label.values():
            while q:
                _unmatched_subtree(q.popleft())

    _score(t1, t2)
    if total == 0:
        return 1.0
    return matches / total