from models import Node


def serialize_node(node: Node) -> str:
    if node.node_type == "text":
        return node.value or ""

    if node.node_type != "element":
        return ""

    if node.label == "link":
        target = ""
        label = ""

        for child in node.children:
            if child.label == "target" and child.node_type == "text":
                target = child.value or ""
            elif child.label == "label" and child.node_type == "text":
                label = child.value or ""

        if target and label:
            return f"[[{target}|{label}]]"
        if target:
            return f"[[{target}]]"
        return ""

    if node.label.startswith("template:"):
        template_name = node.label.split(":", 1)[1]
        parts = [template_name]

        def sort_key(child: Node):
            if child.label.startswith("arg"):
                try:
                    return (0, int(child.label[3:]))
                except ValueError:
                    return (0, 999999)
            return (1, child.label)

        for child in sorted(node.children, key=sort_key):
            value = serialize_children(child).strip()

            if child.label.startswith("arg"):
                if value:
                    parts.append(value)
            else:
                parts.append(f"{child.label}={value}")

        return "{{" + "|".join(parts) + "}}"

    return serialize_children(node)


def serialize_children(node: Node) -> str:
    parts = []

    for child in node.children:
        rendered = serialize_node(child).strip()
        if rendered:
            parts.append(rendered)

    return "<br>".join(parts)


def tree_to_infobox_wikitext(root: Node) -> str:
    lines = [f"{{{{{root.label}"]

    for child in root.children:
        if child.node_type != "element":
            continue

        value = serialize_children(child)
        lines.append(f"| {child.label} = {value}")

    lines.append("}}")
    return "\n".join(lines)


def save_infobox_wikitext(root: Node, file_path: str) -> None:
    text = tree_to_infobox_wikitext(root)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)