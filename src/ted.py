from __future__ import annotations
from models import Node
from utils import subtree_size
from diff import EditOp
from urllib.parse import quote

def encode_label(label: str) -> str:
    return quote(label, safe="")

def delete_cost(node: Node) -> int:
    return subtree_size(node)


def insert_cost(node: Node) -> int:
    return subtree_size(node)


def update_cost(a: Node, b: Node) -> int:
    cost = 0
    if a.label != b.label:
        cost += 1
    if a.node_type != b.node_type:
        cost += 1
    if (a.value or "") != (b.value or ""):
        cost += 1
    return cost


def sibling_occurrence(children: list[Node], idx: int) -> int:
    target_label = children[idx].label
    count = 0
    for i in range(idx + 1):
        if children[i].label == target_label:
            count += 1
    return count


def ted(a: Node, b: Node) -> int:
    cost, _ = ted_with_ops(a, b, "/root[1]")
    return cost


def ted_with_ops(a: Node, b: Node, current_path: str) -> tuple[int, list[EditOp]]:
    ops: list[EditOp] = []

    root_change_cost = update_cost(a, b)

    if root_change_cost == 0:
        ops.append(EditOp(
            op="match",
            path=current_path,
            old_label=a.label,
            new_label=b.label,
            old_value=a.value,
            new_value=b.value
        ))
    else:
        ops.append(EditOp(
            op="update",
            path=current_path,
            old_label=a.label,
            new_label=b.label,
            old_value=a.value,
            new_value=b.value
        ))

    children_cost, child_ops = child_sequence_distance_with_ops(
        a.children, b.children, current_path
    )

    return root_change_cost + children_cost, ops + child_ops


def child_sequence_distance_with_ops(
    children1: list[Node],
    children2: list[Node],
    parent_path: str
) -> tuple[int, list[EditOp]]:
    m = len(children1)
    n = len(children2)

    dp = [[0] * (n + 1) for _ in range(m + 1)]
    choice = [[None] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] + delete_cost(children1[i - 1])
        choice[i][0] = ("delete", i - 1, None)

    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + insert_cost(children2[j - 1])
        choice[0][j] = ("insert", None, j - 1)

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            delete_option = dp[i - 1][j] + delete_cost(children1[i - 1])
            insert_option = dp[i][j - 1] + insert_cost(children2[j - 1])

            occ1 = sibling_occurrence(children1, i - 1)
            replace_option, _ = ted_with_ops(
                children1[i - 1],
                children2[j - 1],
                f"{parent_path}/{encode_label(children1[i - 1].label)}[{occ1}]"
            )
            match_option = dp[i - 1][j - 1] + replace_option

            best = min(delete_option, insert_option, match_option)
            dp[i][j] = best

            if best == match_option:
                choice[i][j] = ("match_or_update", i - 1, j - 1)
            elif best == delete_option:
                choice[i][j] = ("delete", i - 1, None)
            else:
                choice[i][j] = ("insert", None, j - 1)

    ops: list[EditOp] = []
    i, j = m, n

    while i > 0 or j > 0:
        action, left_idx, right_idx = choice[i][j]

        if action == "match_or_update":
            child1 = children1[left_idx]
            child2 = children2[right_idx]

            occ1 = sibling_occurrence(children1, left_idx)
            child_path = f"{parent_path}/{encode_label(child1.label)}[{occ1}]"

            _, child_sub_ops = ted_with_ops(child1, child2, child_path)
            ops = child_sub_ops + ops
            i -= 1
            j -= 1

        elif action == "delete":
            child1 = children1[left_idx]

            occ1 = sibling_occurrence(children1, left_idx)
            child_path = f"{parent_path}/{encode_label(child1.label)}[{occ1}]"

            ops = [EditOp(
                op="delete",
                path=child_path,
                old_label=child1.label,
                old_value=child1.value
            )] + ops
            i -= 1

        elif action == "insert":
            child2 = children2[right_idx]

            occ2 = sibling_occurrence(children2, right_idx)
            child_path = f"{parent_path}/{encode_label(child2.label)}[{occ2}]"

            ops = [EditOp(
            op="insert",
            path=child_path,
            new_label=child2.label,
            new_value=child2.value,
            new_node=child2.to_dict(),
            insert_pos=right_idx
            )] + ops
            j -= 1

    return dp[m][n], ops