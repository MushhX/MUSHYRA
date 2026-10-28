"""Static lexical-scope analysis for MUSHYRA functions."""

import difflib
from dataclasses import dataclass

from .lexer import MushyraError


@dataclass(frozen=True)
class FunctionScope:
    local_names: frozenset
    global_names: frozenset
    nonlocal_names: frozenset
    free_bindings: tuple = ()
    resolved_globals: frozenset = frozenset()
    definition_span: object = None


def _block_children(statement):
    kind = statement[0]
    if kind == "if":
        yield statement[2]
        for _, branch in statement[3]:
            yield branch
        yield statement[4]
    elif kind == "match":
        for _pattern, _guard, branch in statement[2]:
            yield branch
        yield statement[3]
    elif kind == "try":
        yield statement[1]
        for _pattern, _guard, branch in statement[2]:
            yield branch
        if statement[3] is not None:
            yield statement[3]
    elif kind in ("repeat", "while", "loop", "until", "unless"):
        yield statement[-1]
    elif kind in ("for", "each"):
        yield statement[3]


def _pattern_names(pattern):
    if pattern[0] == "pattern_name":
        yield pattern[1]
    elif pattern[0] == "pattern_list":
        for child in pattern[1]:
            yield from _pattern_names(child)
    elif pattern[0] == "pattern_dict":
        for _key, child in pattern[1]:
            yield from _pattern_names(child)


def _collect_bindings(statements, params):
    locals_ = set(params)
    globals_ = set()
    nonlocals_ = set()
    unknown_imports = False

    def walk(block):
        nonlocal unknown_imports
        for statement in block:
            kind = statement[0]
            if kind in ("let", "assign", "func"):
                locals_.add(statement[1])
                if kind == "func":
                    # A nested function's body belongs to its own lexical scope.
                    continue
            elif kind in ("destructure_let", "destructure_assign"):
                locals_.update(_pattern_names(statement[1]))
            elif kind == "match":
                for pattern, _guard, _branch in statement[2]:
                    locals_.update(_pattern_names(pattern))
            elif kind == "try":
                for pattern, _guard, _branch in statement[2]:
                    locals_.update(_pattern_names(pattern))
            elif kind in ("for", "each"):
                locals_.add(statement[1])
            elif kind == "global":
                globals_.update(statement[1])
            elif kind == "nonlocal":
                nonlocals_.update(statement[1])
            elif kind == "import":
                _, module, alias = statement
                if alias:
                    locals_.add(alias)
                else:
                    unknown_imports = True
            elif kind == "from_import":
                _, _module, items = statement
                for entry in items:
                    if isinstance(entry, tuple):
                        item, alias = entry
                    else:
                        item, alias = entry, None
                    locals_.add(alias or item)
            for child in _block_children(statement):
                walk(child)

    walk(statements)
    if globals_ & nonlocals_:
        raise ValueError("Una variable no puede ser global y nonlocal a la vez")
    if (globals_ | nonlocals_) & set(params):
        raise ValueError("Un parámetro no puede declararse global o nonlocal")
    locals_.difference_update(globals_ | nonlocals_)
    return locals_, globals_, nonlocals_, unknown_imports


def _statement_expressions(statement):
    kind = statement[0]
    if kind in ("destructure_let", "destructure_assign"):
        return (statement[2],)
    if kind in ("let", "assign"):
        return (statement[2],)
    if kind == "index_assign":
        return statement[1:]
    if kind == "slice_assign":
        return statement[1:]
    if kind == "attr_assign":
        return statement[1], statement[3]
    if kind in ("print", "show", "say", "wait", "ask", "expr_stmt"):
        return (statement[1],)
    if kind in ("if", "while", "until", "unless"):
        return (statement[1],)
    if kind == "match":
        return (statement[1], *(guard for _pattern, guard, _body in statement[2] if guard is not None))
    if kind == "try":
        return tuple(guard for _pattern, guard, _body in statement[2] if guard is not None)
    if kind == "throw":
        return (statement[1],)
    if kind == "repeat":
        return (statement[1],)
    if kind in ("for", "each"):
        return (statement[2],)
    if kind == "return":
        return (statement[1],) if statement[1] is not None else ()
    if kind == "assert":
        return statement[1], statement[2]
    if kind == "exit":
        return (statement[1],) if statement[1] is not None else ()
    return ()


def _expression_names(expression, bound_names=frozenset()):
    if expression is None or not isinstance(expression, tuple) or not expression:
        return
    kind = expression[0]
    if kind == "var" and len(expression) > 1:
        if expression[1] not in bound_names:
            yield expression[1], expression
        return
    if kind == "lambda" and len(expression) > 2:
        nested_bound = bound_names | frozenset(expression[1])
        yield from _expression_names(expression[2], nested_bound)
        return
    if kind == "list_comp" and len(expression) > 4:
        variable = expression[2][1]
        nested_bound = bound_names | {variable}
        yield from _expression_names(expression[3], bound_names)
        yield from _expression_names(expression[1], nested_bound)
        yield from _expression_names(expression[4], nested_bound)
        return
    if kind == "dict_comp" and len(expression) > 5:
        variable = expression[3][1]
        nested_bound = bound_names | {variable}
        yield from _expression_names(expression[4], bound_names)
        yield from _expression_names(expression[1], nested_bound)
        yield from _expression_names(expression[2], nested_bound)
        yield from _expression_names(expression[5], nested_bound)
        return
    if kind == "call" and len(expression) > 2:
        if expression[1] not in bound_names:
            yield expression[1], expression
        for arg in expression[2]:
            yield from _expression_names(arg, bound_names)
        return
    items = expression[1:] if isinstance(kind, str) else expression
    for item in items:
        if isinstance(item, tuple):
            yield from _expression_names(item, bound_names)
        elif isinstance(item, list):
            for child in item:
                if isinstance(child, tuple):
                    yield from _expression_names(child, bound_names)


def _function_references(statements):
    references = {}

    def walk(block):
        for statement in block:
            if statement[0] == "func":
                if len(statement) > 4:
                    for _name, expression in statement[4]:
                        for name, node in _expression_names(expression):
                            references.setdefault(name, node)
                continue
            for expression in _statement_expressions(statement):
                for name, node in _expression_names(expression):
                    references.setdefault(name, node)
            for child in _block_children(statement):
                walk(child)

    walk(statements)
    return references


def _module_bindings(statements, initial_names):
    names = set(initial_names)
    has_unknown_import = False

    def walk(block):
        nonlocal has_unknown_import
        for statement in block:
            kind = statement[0]
            if kind in ("let", "assign", "func"):
                names.add(statement[1])
                if kind == "func":
                    continue
            elif kind in ("destructure_let", "destructure_assign"):
                names.update(_pattern_names(statement[1]))
            elif kind == "match":
                for pattern, _guard, _branch in statement[2]:
                    names.update(_pattern_names(pattern))
            elif kind == "try":
                for pattern, _guard, _branch in statement[2]:
                    names.update(_pattern_names(pattern))
            elif kind in ("for", "each"):
                names.add(statement[1])
            elif kind == "import":
                _, _module, alias = statement
                if alias:
                    names.add(alias)
                else:
                    has_unknown_import = True
            elif kind == "from_import":
                for entry in statement[2]:
                    if isinstance(entry, tuple):
                        item, alias = entry
                    else:
                        item, alias = entry, None
                    names.add(alias or item)
            for child in _block_children(statement):
                walk(child)

    walk(statements)
    return names, has_unknown_import


def _location_error(message, filename, statement):
    span = getattr(statement, "span", None)
    return MushyraError(message, filename,
                    span.start_line if span else None,
                    span.start_column if span else None,
                    code="MYR2001")


def analyze_program(statements, filename="<stdin>", initial_names=()):
    """Validate function bindings before execution; return scopes keyed by AST identity."""
    module_names, unknown_module_import = _module_bindings(statements, initial_names)
    scopes = {}
    builtins = {"input", "ask", "len", "type", "str", "int", "float", "range"}
    if not unknown_module_import:
        module_references = _function_references(statements)
        missing = sorted(name for name in module_references
                         if name not in module_names and name not in builtins)
        if missing:
            close = difflib.get_close_matches(missing[0], module_names | builtins,
                                              n=1, cutoff=0.78)
            hint = f"; quizá querías decir {close[0]!r}" if close else ""
            raise _location_error(
                f"Variable {missing[0]!r} no está definida en ningún ámbito conocido{hint}",
                filename, module_references[missing[0]],
            )

    def walk_functions(block, outer_scopes, inherited_declarations=frozenset(),
                       inherited_unknown_imports=False):
        for statement in block:
            for child in _block_children(statement):
                walk_functions(child, outer_scopes, inherited_declarations,
                               inherited_unknown_imports)
            if statement[0] != "func":
                continue
            _, _name, params, body = statement[:4]
            if len(set(params)) != len(params):
                raise _location_error("Una función no puede repetir el nombre de un parámetro",
                                      filename, statement)
            try:
                local_names, global_names, nonlocal_names, unknown_imports = _collect_bindings(body, params)
            except ValueError as exc:
                raise _location_error(str(exc), filename, statement) from exc
            missing_nonlocals = sorted(name for name in nonlocal_names
                                       if not any(name in enclosing for enclosing in outer_scopes))
            if missing_nonlocals:
                raise _location_error(
                    f"nonlocal {missing_nonlocals[0]!r} no existe en una función exterior",
                    filename, statement,
                )
            references = _function_references(body)
            free_bindings = {
                name: next(index + 1 for index, enclosing in enumerate(outer_scopes)
                           if name in enclosing)
                for name in nonlocal_names
            }
            resolved_globals = set(global_names)
            for name in references:
                if name in local_names or name in global_names or name in nonlocal_names:
                    continue
                depth = next((index + 1 for index, enclosing in enumerate(outer_scopes)
                              if name in enclosing), None)
                if depth is not None:
                    free_bindings[name] = depth
                elif not (unknown_imports or inherited_unknown_imports):
                    resolved_globals.add(name)
            scope = FunctionScope(
                frozenset(local_names), frozenset(global_names), frozenset(nonlocal_names),
                tuple(sorted(free_bindings.items())), frozenset(resolved_globals),
                getattr(statement, "span", None),
            )
            scopes[id(statement)] = scope
            visible = set(module_names)
            visible.update(name for enclosing in outer_scopes for name in enclosing)
            visible.update(inherited_declarations)
            visible.update(local_names | global_names | nonlocal_names | set(params) | builtins)
            if not (unknown_module_import or unknown_imports or inherited_unknown_imports):
                missing = sorted(name for name in references if name not in visible)
                if missing:
                    raise _location_error(
                        f"Variable {missing[0]!r} no está definida en ningún ámbito conocido",
                        filename, references[missing[0]],
                    )
            nested_scopes = (frozenset(local_names),) + tuple(outer_scopes)
            walk_functions(body, nested_scopes,
                           inherited_declarations | global_names | nonlocal_names,
                           inherited_unknown_imports or unknown_imports)

    walk_functions(statements, ())
    return scopes
