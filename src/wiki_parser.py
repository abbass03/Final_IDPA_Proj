from models import Node


def split_top_level(text: str, sep: str = "|") -> list[str]:
    parts = []
    current = []
    template_depth = 0
    link_depth = 0
    i = 0

    while i < len(text):
        two = text[i:i+2]

        if two == "{{":
            template_depth += 1
            current.append(two)
            i += 2
            continue

        if two == "}}" and template_depth > 0:
            template_depth -= 1
            current.append(two)
            i += 2
            continue

        if two == "[[":
            link_depth += 1
            current.append(two)
            i += 2
            continue

        if two == "]]" and link_depth > 0:
            link_depth -= 1
            current.append(two)
            i += 2
            continue

        if text[i] == sep and template_depth == 0 and link_depth == 0:
            parts.append("".join(current).strip())
            current = []
            i += 1
            continue

        current.append(text[i])
        i += 1

    if current:
        parts.append("".join(current).strip())

    return parts


def split_top_level_params(infobox_text: str) -> list[str]:
    body = infobox_text.strip()

    if body.startswith("{{"):
        body = body[2:]
    if body.endswith("}}"):
        body = body[:-2]

    return split_top_level(body, sep="|")


def split_on_top_level_br(value: str) -> list[str]:
    parts = []
    current = []
    template_depth = 0
    link_depth = 0
    i = 0

    while i < len(value):
        two = value[i:i+2]
        four = value[i:i+4].lower()
        five = value[i:i+5].lower()

        if two == "{{":
            template_depth += 1
            current.append(two)
            i += 2
            continue

        if two == "}}" and template_depth > 0:
            template_depth -= 1
            current.append(two)
            i += 2
            continue

        if two == "[[":
            link_depth += 1
            current.append(two)
            i += 2
            continue

        if two == "]]" and link_depth > 0:
            link_depth -= 1
            current.append(two)
            i += 2
            continue

        if template_depth == 0 and link_depth == 0:
            if five == "<br/>":
                parts.append("".join(current).strip())
                current = []
                i += 5
                continue
            if four == "<br>":
                parts.append("".join(current).strip())
                current = []
                i += 4
                continue

        current.append(value[i])
        i += 1

    if current:
        parts.append("".join(current).strip())

    return [p for p in parts if p]


def parse_link(value: str) -> Node | None:
    value = value.strip()
    if not (value.startswith("[[") and value.endswith("]]")):
        return None

    inner = value[2:-2].strip()
    parts = split_top_level(inner, sep="|")

    node = Node(label="link", node_type="element")

    if len(parts) >= 1 and parts[0]:
        node.add_child(Node(label="target", node_type="text", value=parts[0].strip()))

    if len(parts) >= 2 and parts[1]:
        node.add_child(Node(label="label", node_type="text", value=parts[1].strip()))

    return node


def parse_template(value: str) -> Node | None:
    value = value.strip()
    if not (value.startswith("{{") and value.endswith("}}")):
        return None

    inner = value[2:-2].strip()
    parts = split_top_level(inner, sep="|")
    if not parts:
        return None

    template_name = parts[0].strip()
    node = Node(label=f"template:{template_name}", node_type="element")

    positional_index = 1

    for part in parts[1:]:
        if "=" in part:
            key, val = part.split("=", 1)
            param_node = Node(label=key.strip(), node_type="element")
            param_node.add_child(Node(label="#text", node_type="text", value=val.strip()))
            node.add_child(param_node)
        else:
            arg_node = Node(label=f"arg{positional_index}", node_type="element")
            arg_node.add_child(Node(label="#text", node_type="text", value=part.strip()))
            node.add_child(arg_node)
            positional_index += 1

    return node


def parse_value_to_children(value: str) -> list[Node]:
    value = value.strip()
    if not value:
        return []

    chunks = split_on_top_level_br(value)
    children = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        link_node = parse_link(chunk)
        if link_node is not None:
            children.append(link_node)
            continue

        template_node = parse_template(chunk)
        if template_node is not None:
            children.append(template_node)
            continue

        children.append(Node(label="#text", node_type="text", value=chunk))

    return children


def parse_infobox_to_tree(infobox_text: str) -> Node:
    parts = split_top_level_params(infobox_text)
    if not parts:
        raise ValueError("Empty infobox")

    template_name = parts[0].strip()
    root = Node(label=template_name, node_type="element")

    for part in parts[1:]:
        if "=" not in part:
            continue

        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()

        param_node = Node(label=key, node_type="element")
        for child in parse_value_to_children(value):
            param_node.add_child(child)

        root.add_child(param_node)

    return root


def load_infobox_tree(file_path: str) -> Node:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return parse_infobox_to_tree(text)