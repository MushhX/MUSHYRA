"""Small, deterministic static checks for MUSHYRA ASTs."""

import difflib
from dataclasses import dataclass


@dataclass(frozen=True)
class LintDiagnostic:
    code: str
    message: str
    severity: str = "warning"
    span: object = None

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "span": self.span.to_dict() if self.span else None,
        }


def _walk(value, bound_names=frozenset()):
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], str):
            kind = value[0]
            if kind == "var" and len(value) > 1 and value[1] in bound_names:
                return
            if kind == "call" and len(value) > 2 and value[1] in bound_names:
                for child in value[2:]:
                    yield from _walk(child, bound_names)
                return
            if kind == "lambda" and len(value) > 2:
                yield value
                yield from _walk(value[2], bound_names | frozenset(value[1]))
                return
            yield value
            if kind == "list_comp" and len(value) > 4:
                variable = value[2][1]
                nested_bound = bound_names | {variable}
                yield from _walk(value[3], bound_names)
                yield from _walk(value[1], nested_bound)
                yield from _walk(value[4], nested_bound)
                return
            if kind == "dict_comp" and len(value) > 5:
                variable = value[3][1]
                nested_bound = bound_names | {variable}
                yield from _walk(value[4], bound_names)
                yield from _walk(value[1], nested_bound)
                yield from _walk(value[2], nested_bound)
                yield from _walk(value[5], nested_bound)
                return
            for child in value[1:]:
                yield from _walk(child, bound_names)
        else:
            for child in value:
                yield from _walk(child, bound_names)


def lint_ast(tree):
    diagnostics = []
    all_nodes = list(_walk(tree))
    used_names = {
        node[1] for node in all_nodes
        if node[0] in ("var", "call") and len(node) > 1
    }

    for node in all_nodes:
        if node[0] == "dict":
            seen = set()
            for key, _value in node[1]:
                if isinstance(key, tuple) and key[0] in ("string", "number", "bool", "null"):
                    try:
                        # Match Python dictionary key semantics used by the
                        # runtime (for example, 1 and true address the same key).
                        canonical = key[1]
                        if canonical in seen:
                            diagnostics.append(LintDiagnostic(
                                "MYR100", f"Clave literal duplicada en diccionario: {key[1]!r}", span=getattr(node, "span", None)
                            ))
                        seen.add(canonical)
                    except TypeError:
                        pass

    def inspect_block(statements):
        terminated = False
        for statement in statements:
            if terminated:
                diagnostics.append(LintDiagnostic(
                    "MYR101", "Código inalcanzable después de return, break, continue, exit o throw",
                    span=getattr(statement, "span", None),
                ))
                break
            kind = statement[0]
            if kind in ("return", "break", "continue", "exit", "throw"):
                terminated = True
            elif kind == "func":
                inspect_block(statement[3])
            elif kind == "if":
                inspect_block(statement[2])
                for _condition, branch in statement[3]:
                    inspect_block(branch)
                inspect_block(statement[4])
            elif kind == "match":
                catch_all_seen = False
                for pattern, guard, branch in statement[2]:
                    if catch_all_seen:
                        diagnostics.append(LintDiagnostic(
                            "MYR105", "Cláusula inalcanzable después de un patrón general",
                            span=getattr(pattern, "span", None),
                        ))
                    inspect_block(branch)
                    if guard is None and pattern[0] in ("pattern_name", "pattern_wildcard"):
                        catch_all_seen = True
                inspect_block(statement[3])
            elif kind == "try":
                inspect_block(statement[1])
                catch_all_seen = False
                for pattern, guard, branch in statement[2]:
                    if catch_all_seen:
                        diagnostics.append(LintDiagnostic(
                            "MYR105", "Cláusula inalcanzable después de un patrón general",
                            span=getattr(pattern, "span", None),
                        ))
                    inspect_block(branch)
                    if guard is None and pattern[0] in ("pattern_name", "pattern_wildcard"):
                        catch_all_seen = True
                if statement[3] is not None:
                    inspect_block(statement[3])
            elif kind in ("repeat", "while", "loop", "until", "unless"):
                inspect_block(statement[-1])
            elif kind in ("for", "each"):
                inspect_block(statement[3])

    inspect_block(tree)

    def bindings(statements, parameters=()):
        declared = set(parameters)
        imported = set()
        for name in parameters:
            declaration_spans.setdefault(name, None)

        def scan(block):
            for statement in block:
                kind = statement[0]
                if kind in ("let", "assign", "func"):
                    declared.add(statement[1])
                    declaration_spans.setdefault(statement[1], getattr(statement, "span", None))
                    if kind == "func":
                        for parameter in statement[2]:
                            declared.add(parameter)
                            declaration_spans.setdefault(parameter, getattr(statement, "span", None))
                        scan(statement[3])
                elif kind in ("destructure_let", "destructure_assign"):
                    for name in pattern_names(statement[1]):
                        declared.add(name)
                        declaration_spans.setdefault(name, getattr(statement, "span", None))
                elif kind in ("import",):
                    _kind, module, alias = statement
                    if alias:
                        declared.add(alias)
                        imported.add(alias)
                        declaration_spans.setdefault(alias, getattr(statement, "span", None))
                elif kind == "from_import":
                    for name, alias in statement[2]:
                        target = alias or name
                        declared.add(target)
                        imported.add(target)
                        declaration_spans.setdefault(target, getattr(statement, "span", None))
                elif kind in ("global", "nonlocal"):
                    declared.update(statement[1])
                elif kind in ("for", "each"):
                    declared.add(statement[1])
                    declaration_spans.setdefault(statement[1], getattr(statement, "span", None))
                    scan(statement[3])
                elif kind == "if":
                    scan(statement[2])
                    for _condition, branch in statement[3]:
                        scan(branch)
                    scan(statement[4])
                elif kind == "match":
                    for pattern, _guard, branch in statement[2]:
                        for name in pattern_names(pattern):
                            declared.add(name)
                            declaration_spans.setdefault(name, getattr(pattern, "span", None))
                        scan(branch)
                    scan(statement[3])
                elif kind == "try":
                    scan(statement[1])
                    for pattern, _guard, branch in statement[2]:
                        for name in pattern_names(pattern):
                            declared.add(name)
                            declaration_spans.setdefault(name, getattr(pattern, "span", None))
                        scan(branch)
                    if statement[3] is not None:
                        scan(statement[3])
                elif kind in ("repeat", "while", "loop", "until", "unless"):
                    scan(statement[-1])

        scan(statements)
        return declared, imported

    declaration_spans = {}

    def pattern_names(pattern):
        if pattern[0] == "pattern_name":
            yield pattern[1]
        elif pattern[0] == "pattern_list":
            for child in pattern[1]:
                yield from pattern_names(child)
        elif pattern[0] == "pattern_dict":
            for _key, child in pattern[1]:
                yield from pattern_names(child)

    declared, imported = bindings(tree)
    declared.add("args")
    known_names = declared | {"input", "ask", "len", "type", "str", "int", "float", "range"}
    if not any(node[0] == "import" and not node[2] for node in all_nodes):
        for node in all_nodes:
            if node[0] == "var" and node[1] not in declared:
                close = difflib.get_close_matches(node[1], known_names, n=1, cutoff=0.78)
                hint = f"; quizá querías decir {close[0]!r}" if close else ""
                diagnostics.append(LintDiagnostic(
                    "MYR102", f"Nombre no declarado: {node[1]!r}{hint}", severity="error",
                    span=getattr(node, "span", None),
                ))
    for name in sorted(declared - used_names):
        if name in imported:
            diagnostics.append(LintDiagnostic("MYR103", f"Importación no usada: {name!r}",
                                               span=declaration_spans.get(name)))
        elif name not in {"args"}:
            diagnostics.append(LintDiagnostic("MYR104", f"Variable no usada: {name!r}",
                                               span=declaration_spans.get(name)))
    return diagnostics
