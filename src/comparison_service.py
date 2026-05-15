from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diff import load_edit_script, save_edit_script
from parser import parse_xml_file
from postprocess import (
    build_comparison_report,
    save_comparison_report,
    save_tree_as_json,
    save_tree_as_wiki_infobox,
    save_tree_as_xml,
    tree_to_dict,
    tree_to_pretty_xml,
    tree_to_wiki_infobox_text,
)
from preprocess import preprocess_tree
from ted import patch_with_ops, ted_with_ops
from utils import (
    count_nodes,
    first_tree_difference,
    similarity_score,
    summarize_edit_ops,
    trees_equal,
)
from wiki_parser import load_infobox_tree
from wiki_serializer import tree_to_infobox_wikitext


def op_to_dict(op: Any) -> dict[str, Any]:
    if hasattr(op, "to_dict"):
        return op.to_dict()
    return dict(op)


def serialize_ops(ops: list[Any]) -> list[dict[str, Any]]:
    return [op_to_dict(op) for op in ops]


def visible_ops(ops: list[Any]) -> list[dict[str, Any]]:
    result = []
    for op in ops:
        kind = op.op if hasattr(op, "op") else str(op.get("op", ""))
        if kind == "match":
            continue
        result.append(op_to_dict(op))
    return result


def build_output_paths(mode: str, output_dir: Path) -> dict[str, str]:
    if mode == "wiki":
        return {
            "edit_script": str(output_dir / "wiki_edit_script.json"),
            "tree1_infobox": str(output_dir / "tree1_infobox.wiki"),
            "tree2_infobox": str(output_dir / "tree2_infobox.wiki"),
            "patched_infobox": str(output_dir / "patched_infobox.wiki"),
            "report": str(output_dir / "comparison_report.txt"),
        }

    return {
        "edit_script": str(output_dir / "edit_script.json"),
        "tree1_xml": str(output_dir / "tree1_normalized.xml"),
        "tree2_xml": str(output_dir / "tree2_normalized.xml"),
        "patched_xml": str(output_dir / "patched_tree.xml"),
        "tree1_json": str(output_dir / "tree1_normalized.json"),
        "tree2_json": str(output_dir / "tree2_normalized.json"),
        "patched_json": str(output_dir / "patched_tree.json"),
        "tree1_infobox": str(output_dir / "tree1_infobox.txt"),
        "tree2_infobox": str(output_dir / "tree2_infobox.txt"),
        "patched_infobox": str(output_dir / "patched_infobox.txt"),
        "report": str(output_dir / "comparison_report.txt"),
    }


def load_source_tree(mode: str, file_path: str):
    if mode == "wiki":
        return load_infobox_tree(file_path)
    return preprocess_tree(parse_xml_file(file_path))


def save_ops_for_method(ops: list[Any], method: str, file_path: str):
    if method == "custom":
        save_edit_script(ops, file_path)
        return load_edit_script(file_path)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(serialize_ops(ops), f, indent=4, ensure_ascii=False)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_documents(
    mode: str,
    file1: str,
    file2: str,
    method: str = "custom",
    output_dir: str = "data/output",
) -> dict[str, Any]:
    mode = mode.lower()
    method = method.lower()

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    tree1 = load_source_tree(mode, file1)
    tree2 = load_source_tree(mode, file2)

    root_path = f"/{tree1.label}[1]" if mode == "wiki" else "/country[1]"
    n1 = count_nodes(tree1)
    n2 = count_nodes(tree2)

    distance, ops = ted_with_ops(tree1, tree2, root_path, method=method)
    similarity = similarity_score(distance, n1, n2)
    summary = summarize_edit_ops(ops)

    output_paths = build_output_paths(mode, output_root)
    loaded_ops = save_ops_for_method(ops, method, output_paths["edit_script"])

    patched_tree = patch_with_ops(tree1, loaded_ops, method=method)
    patch_success = trees_equal(patched_tree, tree2)
    patch_difference = None if patch_success else first_tree_difference(patched_tree, tree2)

    report_text = build_comparison_report(
        file1,
        file2,
        n1,
        n2,
        distance,
        similarity,
        summary,
        patch_success,
        patch_difference,
    )

    save_comparison_report(
        output_paths["report"],
        file1,
        file2,
        n1,
        n2,
        distance,
        similarity,
        summary,
        patch_success,
        patch_difference,
    )

    outputs: dict[str, str] = {"report": report_text}

    if mode == "wiki":
        save_tree_as_wiki_infobox(tree1, output_paths["tree1_infobox"])
        save_tree_as_wiki_infobox(tree2, output_paths["tree2_infobox"])
        save_tree_as_wiki_infobox(patched_tree, output_paths["patched_infobox"])

        outputs.update(
            {
                "tree1_infobox": tree_to_infobox_wikitext(tree1),
                "tree2_infobox": tree_to_infobox_wikitext(tree2),
                "patched_infobox": tree_to_infobox_wikitext(patched_tree),
            }
        )
    else:
        save_tree_as_xml(tree1, output_paths["tree1_xml"])
        save_tree_as_xml(tree2, output_paths["tree2_xml"])
        save_tree_as_xml(patched_tree, output_paths["patched_xml"])

        save_tree_as_json(tree1, output_paths["tree1_json"])
        save_tree_as_json(tree2, output_paths["tree2_json"])
        save_tree_as_json(patched_tree, output_paths["patched_json"])

        save_tree_as_wiki_infobox(tree1, output_paths["tree1_infobox"])
        save_tree_as_wiki_infobox(tree2, output_paths["tree2_infobox"])
        save_tree_as_wiki_infobox(patched_tree, output_paths["patched_infobox"])

        outputs.update(
            {
                "tree1_xml": tree_to_pretty_xml(tree1),
                "tree2_xml": tree_to_pretty_xml(tree2),
                "patched_xml": tree_to_pretty_xml(patched_tree),
                "tree1_json": json.dumps({tree1.label: tree_to_dict(tree1)}, indent=4, ensure_ascii=False),
                "tree2_json": json.dumps({tree2.label: tree_to_dict(tree2)}, indent=4, ensure_ascii=False),
                "patched_json": json.dumps({patched_tree.label: tree_to_dict(patched_tree)}, indent=4, ensure_ascii=False),
                "tree1_infobox": tree_to_wiki_infobox_text(tree1),
                "tree2_infobox": tree_to_wiki_infobox_text(tree2),
                "patched_infobox": tree_to_wiki_infobox_text(patched_tree),
            }
        )

    return {
        "mode": mode,
        "method": method,
        "file1": file1,
        "file2": file2,
        "stats": {
            "tree1_nodes": n1,
            "tree2_nodes": n2,
            "distance": distance,
            "similarity": round(similarity, 4),
        },
        "summary": summary,
        "patch": {
            "success": patch_success,
            "difference": patch_difference,
        },
        "ops": {
            "all": serialize_ops(ops),
            "visible": visible_ops(ops),
        },
        "trees": {
            "tree1": tree1.to_dict(),
            "tree2": tree2.to_dict(),
            "patched": patched_tree.to_dict(),
        },
        "outputs": outputs,
        "output_paths": output_paths,
    }
