from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class EditOp:
    op: str
    path: str
    old_label: Optional[str] = None
    new_label: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    new_node: Optional[dict] = None
    insert_pos: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "op": self.op,
            "path": self.path,
            "old_label": self.old_label,
            "new_label": self.new_label,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "new_node": self.new_node,
            "insert_pos": self.insert_pos,
        }


def save_edit_script(ops: list[EditOp], file_path: str) -> None:
    visible_ops = [op.to_dict() for op in ops if op.op != "match"]
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(visible_ops, f, indent=4, ensure_ascii=False)


def load_edit_script(file_path: str) -> list[EditOp]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [EditOp(**item) for item in data]