"""Pure helpers for parsing LeetCode's Python starter code."""

import ast
import hashlib
import re


def _matching_parenthesis(source, opening_index):
    depth = 0
    for index in range(opening_index, len(source)):
        character = source[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Could not find the end of the Python method signature")


def _split_top_level(value):
    parts = []
    start = 0
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for index, character in enumerate(value):
        if character in "([{":
            stack.append(character)
        elif character in ")]}":
            if stack and stack[-1] == pairs[character]:
                stack.pop()
        elif character == "," and not stack:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    return [part for part in parts if part]


def parse_python_signature(source):
    """Return ``(parameter_names, parameter_types, return_type)``.

    LeetCode starter code commonly has an empty function body, so using
    ``ast.parse`` is not reliable here.  This parser only reads the first
    method definition and understands nested generic annotations.
    """

    match = re.search(r"(?m)^\s*def\s+[A-Za-z_]\w*\s*\(", source)
    if not match:
        raise ValueError("Could not find a Python method in LeetCode's starter code")

    opening_index = source.find("(", match.start())
    closing_index = _matching_parenthesis(source, opening_index)
    parameters_text = source[opening_index + 1:closing_index]

    signature_tail = source[closing_index + 1:]
    colon_index = signature_tail.find(":")
    if colon_index < 0:
        raise ValueError("Could not find the end of the Python method signature")
    signature_tail = signature_tail[:colon_index].strip()
    return_type = signature_tail[2:].strip() if signature_tail.startswith("->") else ""

    names = []
    types = []
    for parameter in _split_top_level(parameters_text):
        if parameter in {"self", "cls", "*", "/"}:
            continue
        parameter = parameter.lstrip("*")
        name_and_type = _split_top_level_assignment(parameter)
        if ":" in name_and_type:
            name, annotation = name_and_type.split(":", 1)
        else:
            name, annotation = name_and_type, ""
        names.append(name.strip())
        types.append(annotation.strip())

    if not names:
        raise ValueError("The Python method does not have any testcase parameters")
    return names, types, return_type


def _split_top_level_assignment(parameter):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for index, character in enumerate(parameter):
        if character in "([{":
            stack.append(character)
        elif character in ")]}":
            if stack and stack[-1] == pairs[character]:
                stack.pop()
        elif character == "=" and not stack:
            return parameter[:index].strip()
    return parameter.strip()


def default_return_statement(return_type):
    normalized = return_type.replace(" ", "")
    if normalized == "int":
        return "return -9000000000000000"
    if normalized == "float":
        return "return float('inf')"
    return "return"


def _compact_comparison(node, literal_threshold):
    if not (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
    ):
        return node, False, 0

    literal_node = node.comparators[0]
    try:
        literal_value = ast.literal_eval(literal_node)
    except (ValueError, TypeError, SyntaxError):
        return node, False, 0

    literal_text = repr(literal_value)
    cost = len(literal_text)
    if cost <= literal_threshold or not isinstance(
        literal_value,
        (list, tuple, dict, str, bytes),
    ):
        return node, False, cost

    digest = hashlib.sha256(literal_text.encode("utf-8")).hexdigest()
    left_source = ast.unparse(node.left)
    compact_node = ast.parse(
        "hashlib.sha256(repr({}).encode('utf-8')).hexdigest() == {!r}".format(
            left_source,
            digest,
        ),
        mode="eval",
    ).body
    return compact_node, True, cost


def _compact_condition(node, literal_threshold):
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        compacted = []
        used_hash = False
        for value in node.values:
            new_value, value_used_hash, cost = _compact_comparison(
                value,
                literal_threshold,
            )
            compacted.append((cost, new_value))
            used_hash = used_hash or value_used_hash
        # Cheap scalar checks such as `target == 9` should short-circuit
        # before hashing a large input collection.
        compacted.sort(key=lambda item: item[0])
        node.values = [value for _, value in compacted]
        return node, used_hash

    compacted, used_hash, _ = _compact_comparison(node, literal_threshold)
    return compacted, used_hash


def compact_submission_source(source, literal_threshold=200):
    """Shrink generated literal comparisons while keeping the archive intact.

    The local data file remains a full testcase archive.  Only code pasted
    into LeetCode replaces very large built-in literals with stable SHA-256
    comparisons, preventing the submission from crossing LeetCode's source
    length limit.
    """
    output_lines = []
    used_hash = False
    for line in source.splitlines():
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        if not stripped.startswith("if "):
            output_lines.append(line)
            continue

        try:
            statement = ast.parse(stripped).body[0]
        except SyntaxError:
            output_lines.append(line)
            continue
        if not (
            isinstance(statement, ast.If)
            and len(statement.body) == 1
            and isinstance(statement.body[0], ast.Return)
            and not statement.orelse
        ):
            output_lines.append(line)
            continue

        condition, condition_used_hash = _compact_condition(
            statement.test,
            literal_threshold,
        )
        if not condition_used_hash:
            output_lines.append(line)
            continue

        return_node = statement.body[0]
        return_source = (
            "return"
            if return_node.value is None
            else "return {}".format(ast.unparse(return_node.value))
        )
        output_lines.append(
            "{}if {}: {}".format(indent, ast.unparse(condition), return_source)
        )
        used_hash = True

    if used_hash and not any(line.strip() == "import hashlib" for line in output_lines):
        output_lines.insert(0, "import hashlib")
    return "\n".join(output_lines)
