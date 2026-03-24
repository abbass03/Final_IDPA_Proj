from __future__ import annotations

from typing import Optional, Union

from .edit_script import NJTedResult, TedResult
from .tree import TreeNode
from .chawathe import chawathe_tree_to_ld_pairs, compute_ted_chawathe
from .nj import compute_ted_nj

ALGORITHM_CHAWATHE = "chawathe"
ALGORITHM_NJ = "nj"


def compute_ted(
    source_root: TreeNode,
    target_root: TreeNode,
    *,
    algorithm: str = ALGORITHM_CHAWATHE,
    coerce_root_label: Optional[str] = None,
) -> Union[TedResult, NJTedResult]:
    al = (algorithm or "").lower()
    if al == ALGORITHM_NJ:
        return compute_ted_nj(
            source_root, target_root, coerce_root_label=coerce_root_label
        )
    return compute_ted_chawathe(
        source_root, target_root, coerce_root_label=coerce_root_label
    )


def tree_to_ld_pairs(root: TreeNode):
    return chawathe_tree_to_ld_pairs(root)