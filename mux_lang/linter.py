"""Small, deterministic static checks for Mux ASTs."""

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


def _walk(value):
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], str):
            yield value
            for child in value[1:]:
                yield from _walk(child)
        else:
            for child in value:
                yield from _walk(child)


def lint_ast(tree):
    diagnostics = []
    all_nodes = list(_walk(tree))
    used_names = {node[1] for node in all_nodes if node[0] == "var" and len(node) > 1}

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
                                "MUX100", f"Clave literal duplicada en diccionario: {key[1]!r}", span=getattr(node, "span", None)
                            ))
                        seen.add(canonical)
                    except TypeError:
                        pass

    def inspect_block(statements):
        terminated = False
        for statement in statements:
            if terminated:
                diagnostics.append(LintDiagnostic(
                    "MUX101", "Código inalcanzable después de return, break, continue o exit",
                    span=getattr(statement, "span", None),
                ))
                break
            kind = statement[0]
            if kind in ("return", "break", "continue", "exit"):
                terminated = True
            elif kind == "func":
                inspect_block(statement[3])
            elif kind == "if":
                inspect_block(statement[2])
                for _condition, branch in statement[3]:
                    inspect_block(branch)
                inspect_block(statement[4])
            elif kind in ("repeat", "while", "loop", "until", "unless"):
                inspect_block(statement[-1])
            elif kind in ("for", "each"):
                inspect_block(statement[3])

    inspect_block(tree)

    def bindings(statements, parameters=()):
        declared = set(parameters)
        imported = set()

        def scan(block):
            for statement in block:
                kind = statement[0]
                if kind in ("let", "assign", "func"):
                    declared.add(statement[1])
                    if kind == "func":
                        declared.update(statement[2])
                        scan(statement[3])
                elif kind in ("import",):
                    _kind, module, alias = statement
                    if alias:
                        declared.add(alias)
                        imported.add(alias)
                elif kind == "from_import":
                    for name, alias in statement[2]:
                        target = alias or name
                        declared.add(target)
                        imported.add(target)
                elif kind in ("global", "nonlocal"):
                    declared.update(statement[1])
                elif kind in ("for", "each"):
                    declared.add(statement[1])
                    scan(statement[3])
                elif kind == "if":
                    scan(statement[2])
                    for _condition, branch in statement[3]:
                        scan(branch)
                    scan(statement[4])
                elif kind in ("repeat", "while", "loop", "until", "unless"):
                    scan(statement[-1])

        scan(statements)
        return declared, imported

    declared, imported = bindings(tree)
    declared.add("args")
    if not any(node[0] == "import" and not node[2] for node in all_nodes):
        for node in all_nodes:
            if node[0] == "var" and node[1] not in declared:
                diagnostics.append(LintDiagnostic(
                    "MUX102", f"Nombre no declarado: {node[1]!r}", severity="error",
                    span=getattr(node, "span", None),
                ))
    for name in sorted(declared - used_names):
        if name in imported:
            diagnostics.append(LintDiagnostic("MUX103", f"Importación no usada: {name!r}"))
        elif name not in {"args"}:
            diagnostics.append(LintDiagnostic("MUX104", f"Variable no usada: {name!r}"))
    return diagnostics
