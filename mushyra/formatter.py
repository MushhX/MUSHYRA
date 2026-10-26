"""Conservative source formatter for valid MUSHYRA programs."""

from .lexer import Lexer


OPENERS = {"IF", "MATCH", "REPEAT", "WHILE", "FOR", "FUNC", "LOOP", "UNTIL", "UNLESS", "EACH"}
CLOSERS = {"END", "ELSE", "ELIF"}
DELIMITER_PAIRS = {"LPAREN": "RPAREN", "LBRACKET": "RBRACKET", "LBRACE": "RBRACE"}
DELIMITER_CLOSE = {value: key for key, value in DELIMITER_PAIRS.items()}


def format_source(source: str, indent_width: int = 4) -> str:
    """Normalize block indentation and trailing whitespace without rewriting expressions."""
    if not isinstance(indent_width, int) or isinstance(indent_width, bool) or not 1 <= indent_width <= 8:
        raise ValueError("indent_width debe estar entre 1 y 8")
    tokens = Lexer(source).tokenize()
    by_line = {}
    for token in tokens:
        if token.type != "NEWLINE":
            by_line.setdefault(token.line, []).append(token)

    output = []
    block_depth = 0
    delimiters = []
    match_depths = []
    for line_number, line in enumerate(source.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        stripped = line.strip()
        if not stripped:
            output.append("")
            continue

        line_tokens = by_line.get(line_number, [])
        first = line_tokens[0].type if line_tokens else None
        closing_match = first == "END" and match_depths and block_depth == match_depths[-1] + 2
        matching_case = (first in ("CASE", "ELSE") and match_depths
                         and block_depth == match_depths[-1] + 2)
        if closing_match:
            structural_depth = match_depths.pop()
        elif matching_case:
            structural_depth = match_depths[-1] + 1
        else:
            structural_depth = max(0, block_depth - 1) if first in CLOSERS else block_depth
        if delimiters:
            indent_level = delimiters[-1][1] if first in DELIMITER_CLOSE else delimiters[-1][1] + 1
        else:
            indent_level = structural_depth
        if first is None and stripped.startswith("#"):
            indent_level = delimiters[-1][1] + 1 if delimiters else block_depth
        output.append(" " * (indent_level * indent_width) + stripped)

        for token in line_tokens:
            if token.type in DELIMITER_PAIRS:
                delimiters.append((DELIMITER_PAIRS[token.type], indent_level))
            elif token.type in DELIMITER_CLOSE and delimiters and delimiters[-1][0] == token.type:
                delimiters.pop()

        if first == "END":
            block_depth = structural_depth
        elif first == "MATCH":
            match_depths.append(structural_depth)
            block_depth = structural_depth + 1
        elif first == "CASE" and match_depths:
            block_depth = match_depths[-1] + 2
        elif first == "ELSE" and matching_case:
            block_depth = match_depths[-1] + 2
        elif first in ("ELSE", "ELIF"):
            block_depth = structural_depth + 1
        elif first in OPENERS or (first == "NUMBER" and any(token.type == "TIMES" for token in line_tokens)):
            block_depth += 1

    formatted = "\n".join(output)
    if source.endswith(("\n", "\r")):
        return formatted + "\n"
    return formatted
