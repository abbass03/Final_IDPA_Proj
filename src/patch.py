import copy
import re
from urllib.parse import quote, unquote

from models import Node
from diff import EditOp


def encode_label(label: str) -> str:
    return quote(label, safe="")


def decode_label(label: str) -> str:
    return unquote(label)


def clone_tree(root: Node) -> Node:
    return copy.deepcopy(root)


def parse_path(path: str) -> list[tuple[str, int]]:
    parts = [p for p in path.strip("/").split("/") if p]
    parsed = []

    for part in parts:
        match = re.match(r"(.+)\[(\d+)\]$", part)
        if not match:
            raise ValueError(f"Invalid path segment: {part}")
        raw_label = match.group(1)
        label = decode_label(raw_label)
        index = int(match.group(2))
        parsed.append((label, index))

    return parsed


def find_node_by_path(root: Node, path: str) -> Node:
    parts = parse_path(path)

    root_label, root_index = parts[0]
    if root.label != root_label or root_index != 1:
        raise ValueError(f"Root mismatch: expected {root.label}[1], got {root_label}[{root_index}]")

    current = root

    for label, index in parts[1:]:
        matching_children = [child for child in current.children if child.label == label]
        if index < 1 or index > len(matching_children):
            raise ValueError(f"Path not found: {path}")
        current = matching_children[index - 1]

    return current


def find_parent_and_target(path_root: Node, path: str) -> tuple[Node, Node]:
    parts = parse_path(path)
    if len(parts) < 2:
        raise ValueError("Cannot get parent of root")

    parent_path = "/" + "/".join(f"{encode_label(label)}[{index}]" for label, index in parts[:-1])
    parent = find_node_by_path(path_root, parent_path)
    target = find_node_by_path(path_root, path)
    return parent, target


def find_child_position(parent: Node, target: Node) -> int:
    for i, child in enumerate(parent.children):
        if child is target:
            return i
    raise ValueError("Target child not found in parent")


def apply_update(node: Node, op: EditOp) -> None:
    if op.new_node is not None:
        # Full subtree replacement (promoted DELETE+INSERT pair): copy both
        # value and children from the target node so the tree matches exactly.
        replacement = Node.from_dict(op.new_node)
        node.label = replacement.label
        node.value = replacement.value
        node.children = replacement.children
        return
    if op.new_label is not None:
        node.label = op.new_label
    if op.new_value is not None or op.old_value is not None:
        node.value = op.new_value


def apply_delete(root: Node, op: EditOp) -> None:
    parent, target = find_parent_and_target(root, op.path)
    pos = find_child_position(parent, target)
    del parent.children[pos]


def build_node_from_op(op: EditOp) -> Node:
    if op.new_node is not None:
        return Node.from_dict(op.new_node)

    return Node(
        label=op.new_label if op.new_label is not None else "unknown",
        value=op.new_value,
        node_type="text" if (op.new_label == "#text") else "element"
    )


def apply_insert(root: Node, op: EditOp) -> None:
    parts = parse_path(op.path)
    if len(parts) < 2:
        raise ValueError("Cannot insert at root level in this version")

    parent_path = "/" + "/".join(f"{encode_label(label)}[{index}]" for label, index in parts[:-1])
    parent = find_node_by_path(root, parent_path)

    new_node = build_node_from_op(op)

    if op.insert_pos is None or op.insert_pos < 0 or op.insert_pos > len(parent.children):
        parent.add_child(new_node)
    else:
        parent.children.insert(op.insert_pos, new_node)


def path_depth(path: str) -> int:
    return len([p for p in path.strip("/").split("/") if p])


def parsed_last_index(path: str) -> int:
    parts = parse_path(path)
    if not parts:
        return 0
    return parts[-1][1]


def apply_edit_script(root: Node, ops: list[EditOp]) -> Node:
    patched = clone_tree(root)

    visible_ops = [op for op in ops if op.op != "match"]

    delete_ops = [op for op in visible_ops if op.op == "delete"]
    update_ops = [op for op in visible_ops if op.op == "update"]
    insert_ops = [op for op in visible_ops if op.op == "insert"]

    # When TED's cost model prefers DELETE+INSERT (cost=2) over UPDATE (cost=3)
    # for leaf nodes with very different values, it emits two separate ops at the
    # same path.  Promote any such pair to a single in-place UPDATE.
    # Restriction: only promote at path depth >= 3 (i.e. #text nodes and deeper).
    # Depth-2 structural fields may need to MOVE position (different insert_pos),
    # so promoting them to an in-place UPDATE would anchor them at the wrong slot.
    delete_by_path = {op.path: op for op in delete_ops}
    promoted: list[EditOp] = []
    consumed: set[str] = set()
    remaining_inserts: list[EditOp] = []

    for ins in insert_ops:
        if ins.path in delete_by_path and path_depth(ins.path) >= 3:
            del_op = delete_by_path[ins.path]
            # Store new_node so apply_update can replace children too.
            promoted.append(EditOp(
                op="update",
                path=ins.path,
                old_label=del_op.old_label,
                new_label=ins.new_label if ins.new_label is not None else del_op.old_label,
                old_value=del_op.old_value,
                new_value=ins.new_value,
                new_node=ins.new_node,
            ))
            consumed.add(ins.path)
        else:
            remaining_inserts.append(ins)

    # The promoted UPDATE replaces the entire subtree at that path.  Any
    # INSERT or DELETE ops targeting descendants of that path are now wrong
    # (they would operate on an already-correct subtree).  Remove them.
    def _is_descendant(child_path: str, parent_path: str) -> bool:
        return child_path.startswith(parent_path + "/")

    delete_ops = [
        op for op in delete_ops
        if op.path not in consumed
        and not any(_is_descendant(op.path, pp) for pp in consumed)
    ]
    remaining_inserts = [
        op for op in remaining_inserts
        if not any(_is_descendant(op.path, pp) for pp in consumed)
    ]
    update_ops = update_ops + promoted
    insert_ops = remaining_inserts

    delete_ops.sort(
        key=lambda op: (path_depth(op.path), parsed_last_index(op.path)),
        reverse=True
    )

    insert_ops.sort(
        key=lambda op: (
            path_depth(op.path),
            op.insert_pos if op.insert_pos is not None else 10**9
        )
    )

    # Ops that touch tokenized_value / parsed_date / parsed_measurement subtrees
    # are unreliable: sequential position drift inside long token sequences causes
    # wrong child counts.  Skip them entirely — we rebuild those children below.
    _SEMANTIC_LABELS = {"tokenized_value", "parsed_date", "parsed_measurement",
                        "number_token", "word_token", "symbol_token",
                        "direction_token", "month_token", "unit_token",
                        "year", "month", "day", "number", "unit", "currency"}

    def _touches_semantic(path: str) -> bool:
        return any(seg.split("[")[0] in _SEMANTIC_LABELS
                   for seg in path.lstrip("/").split("/"))

    # Pre-resolve all UPDATE targets before applying any DELETEs.
    # This prevents occurrence-count drift: when multiple UPDATEs relabel nodes
    # to the same label (e.g. riksdag_speaker→prime_minister and prime_minister→
    # chief_justice), sequential path lookups after the first relabeling pick up
    # the wrong node.  Storing direct node references up front avoids that.
    update_targets: list[tuple] = []
    for op in update_ops:
        try:
            node = find_node_by_path(patched, op.path)
            update_targets.append((node, op))
        except ValueError:
            pass

    # Deletes run first: if TED relabels field A→B (UPDATE) and also deletes the
    # original field B, running UPDATE first would create two B nodes and the
    # occurrence-based DELETE lookup would then remove the wrong one.
    for op in delete_ops:
        if _touches_semantic(op.path):
            continue
        try:
            apply_delete(patched, op)
        except ValueError:
            continue

    # Apply updates using pre-resolved node references (not path lookups).
    for node, op in update_targets:
        apply_update(node, op)

    for op in insert_ops:
        if _touches_semantic(op.path):
            continue
        try:
            apply_insert(patched, op)
        except ValueError:
            continue

    # After all structural changes, rebuild every #text node's semantic children
    # (tokenized_value, parsed_date, parsed_measurement) from its current value.
    # This is equivalent to re-preprocessing only the text-leaf layer, so the
    # analysis always matches what preprocess_tree would produce for the new value.
    from preprocess import (
        build_date_analysis,
        build_measurement_analysis,
        build_token_analysis,
        normalize_text,
    )

    def _rebuild_text_node(node: Node) -> None:
        if node.node_type == "text" and node.value is not None:
            node.value = normalize_text(node.value)
            children = []
            d = build_date_analysis(node.value)
            if d:
                children.append(d)
            m = build_measurement_analysis(node.value)
            if m:
                children.append(m)
            t = build_token_analysis(node.value)
            if t:
                children.append(t)
            node.children = children
            return  # don't recurse into the newly built children
        for child in node.children:
            _rebuild_text_node(child)

    _rebuild_text_node(patched)
    return patched