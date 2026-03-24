from __future__ import annotations

from ted_custom import ted_with_ops as ted_custom_with_ops
from ted_adapter import node_to_lit, lit_to_node
from lit_ted.ted import compute_ted
from lit_ted.patch import apply_patch_from_dict
from lit_ted.tree import TreeNode as LitTreeNode


def ted_with_ops(a, b, current_path: str, method: str = "custom"):
    """
    Unified TED entry point.

    method:
      - custom
      - chawathe
      - nj
    """
    method = (method or "custom").lower()

    if method == "custom":
        distance, ops = ted_custom_with_ops(a, b, current_path)
        return distance, ops

    source = node_to_lit(a)
    target = node_to_lit(b)

    result = compute_ted(source, target, algorithm=method)
    ops = [op.to_dict() for op in result.operations]
    return result.distance, ops


def patch_with_ops(source_tree, ops, method: str = "custom"):
    method = (method or "custom").lower()

    if method == "custom":
        from patch import apply_edit_script
        return apply_edit_script(source_tree, ops)

    source = node_to_lit(source_tree)
    patched_dict = apply_patch_from_dict(
        source.to_dict(),
        {"operations": ops},
        algorithm=method,
    )
    patched_lit = LitTreeNode.from_dict(patched_dict)
    return lit_to_node(patched_lit)