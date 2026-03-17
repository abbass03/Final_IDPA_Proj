from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Node:
    label: str
    node_type: str = "element"
    value: Optional[str] = None
    children: List["Node"] = field(default_factory=list)

    def add_child(self, child: "Node") -> None:
        self.children.append(child)

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def pretty(self, level: int = 0) -> str:
        indent = "  " * level
        if self.node_type == "text":
            line = f"{indent}- TEXT: {self.value}"
        else:
            line = f"{indent}- {self.node_type.upper()}: {self.label}"
        parts = [line]
        for child in self.children:
            parts.append(child.pretty(level + 1))
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "node_type": self.node_type,
            "value": self.value,
            "children": [child.to_dict() for child in self.children],
        }

    @staticmethod
    def from_dict(data: dict) -> "Node":
        node = Node(
            label=data["label"],
            node_type=data.get("node_type", "element"),
            value=data.get("value"),
        )
        for child_data in data.get("children", []):
            node.add_child(Node.from_dict(child_data))
        return node