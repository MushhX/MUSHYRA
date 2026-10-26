"""Recursive-descent parser for Mux."""

import ast
from typing import Any, Dict, List, Optional, Tuple

from .ast_nodes import ASTNode, SourceSpan
from .lexer import MuxError, Token


class Parser:
    """Parse tokens into the interpreter's compact tuple AST."""

    MAX_BLOCK_NESTING = 128
    MAX_EXPRESSION_NESTING = 128
    MAX_UNARY_NESTING = 128
    MAX_BINARY_OPERATORS = 128

    def __init__(self, tokens: List[Tuple], path: Optional[str] = None):
        self.path = path
        normalized = []
        for token in tokens:
            if isinstance(token, Token):
                normalized.append(token)
            else:  # Keep the public parser compatible with legacy 3-tuples.
                token_type, value, line = token[:3]
                normalized.append(Token(token_type, value, line, 1, 0))
        self.tokens = self._fold_continuation_lines(normalized)
        self.pos = 0
        self.source_map: Dict[int, Token] = {}
        self.expression_spans: Dict[int, SourceSpan] = {}
        self.node_spans: Dict[int, SourceSpan] = {}
        self.function_depth = 0
        self.loop_depth = 0
        self.block_nesting = 0
        self.expression_nesting = 0
        self.unary_nesting = 0
        self.expression_operator_counts = []

    @staticmethod
    def _fold_continuation_lines(tokens: List[Token]) -> List[Token]:
        """Ignore physical newlines only while inside a delimited expression."""
        result = []
        depth = 0
        opening = {"LPAREN", "LBRACKET", "LBRACE"}
        closing = {"RPAREN", "RBRACKET", "RBRACE"}
        for token in tokens:
            if token.type == "NEWLINE" and depth:
                continue
            result.append(token)
            if token.type in opening:
                depth += 1
            elif token.type in closing:
                depth = max(0, depth - 1)
        return result

    def current(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def peek(self, offset: int = 1) -> Optional[Token]:
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else None

    def advance(self) -> Optional[Token]:
        token = self.current()
        if token is not None:
            self.pos += 1
        return token

    def skip_newlines(self) -> None:
        while self.current() and self.current().type == "NEWLINE":
            self.advance()

    def error(self, message: str, token: Optional[Token] = None) -> MuxError:
        token = token or self.current()
        return MuxError(
            message,
            path=self.path,
            line=token.line if token else None,
            column=token.column if token else None,
            incomplete=token is None,
        )

    def expect(self, token_type: str) -> Token:
        token = self.current()
        if token is None or token.type != token_type:
            actual = token.type if token else "fin de archivo"
            error = self.error(f"Se esperaba {token_type}, se encontró {actual}", token)
            error.incomplete = token is None
            raise error
        self.advance()
        return token

    def parse(self) -> List[Any]:
        statements = []
        self.skip_newlines()
        while self.current():
            before = self.pos
            statement = self.parse_statement()
            if statement is not None:
                statements.append(statement)
            if self.pos == before:
                raise self.error("El parser no pudo avanzar")
            if self.current() and self.current().type != "NEWLINE":
                raise self.error("Se esperaba un salto de línea entre declaraciones")
            self.skip_newlines()
        return self._type_tree(statements)

    @staticmethod
    def _span_from_tokens(start, end):
        if start is None or end is None:
            return None
        return SourceSpan(
            start.line, start.column, end.line,
            end.column + (end.end_offset - end.offset), start.offset, end.end_offset,
        )

    def _type_tree(self, tree):
        """Convert tuple AST records to ASTNode while retaining tuple behavior."""
        node_kinds = {
            "print", "if", "repeat", "while", "for", "func", "return", "break",
            "continue", "assert", "show", "say", "wait", "exit", "pass", "loop",
            "until", "unless", "each", "expr_stmt", "import", "from_import", "let",
            "assign", "index_assign", "slice_assign", "attr_assign", "global", "nonlocal", "number",
            "string", "bool", "null", "var", "list", "tuple", "dict", "index", "attr",
            "method", "unary", "binop", "builtin", "call",
            "named_arg", "pattern_name", "pattern_list", "destructure_let",
            "destructure_assign", "slice",
        }
        old_source_map = self.source_map
        new_source_map = {}

        def convert(value):
            if isinstance(value, list):
                return [convert(item) for item in value]
            if not isinstance(value, tuple):
                return value
            converted = tuple(convert(item) for item in value)
            if not value or not isinstance(value[0], str) or value[0] not in node_kinds:
                return converted
            span = self.node_spans.get(id(value)) or self.expression_spans.get(id(value))
            if span is None:
                child_spans = [item.span for item in converted[1:] if isinstance(item, ASTNode) and item.span]
                if child_spans:
                    span = SourceSpan(
                        min(item.start_line for item in child_spans),
                        min(item.start_column for item in child_spans),
                        max(item.end_line for item in child_spans),
                        max(item.end_column for item in child_spans),
                        min(item.start_offset for item in child_spans),
                        max(item.end_offset for item in child_spans),
                    )
            node = ASTNode(converted, span)
            token = old_source_map.get(id(value))
            if token is not None:
                new_source_map[id(node)] = token
            return node

        typed_tree = convert(tree)
        # Keep the mapping object stable: embedders may pass it to Interpreter
        # before calling parse(), and imported modules do the same internally.
        old_source_map.clear()
        old_source_map.update(new_source_map)
        self.source_map = old_source_map
        return typed_tree

    def parse_statement(self):
        self.skip_newlines()
        token = self.current()
        if token is None:
            return None
        kind = token.type

        if kind == "IMPORT":
            stmt = self.parse_import()
        elif kind == "FROM":
            stmt = self.parse_from_import()
        elif kind == "LET":
            stmt = self.parse_let()
        elif kind == "PRINT":
            self.advance()
            self.expect("LPAREN")
            expr = self.parse_expression()
            self.expect("RPAREN")
            stmt = ("print", expr)
        elif kind == "IF":
            stmt = self.parse_if()
        elif kind == "REPEAT":
            stmt = self.parse_repeat()
        elif kind == "WHILE":
            stmt = self.parse_while()
        elif kind == "FOR":
            stmt = self.parse_for()
        elif kind == "FUNC":
            stmt = self.parse_func()
        elif kind == "RETURN":
            if self.function_depth == 0:
                raise self.error("return solo puede usarse dentro de una función", token)
            self.advance()
            value = None if self._at_statement_end() else self.parse_expression()
            stmt = ("return", value)
        elif kind in ("BREAK", "CONTINUE"):
            self.advance()
            if self.loop_depth == 0:
                word = "break" if kind == "BREAK" else "continue"
                raise self.error(f"{word} solo puede usarse dentro de un bucle", token)
            stmt = ("break",) if kind == "BREAK" else ("continue",)
        elif kind == "ASSERT":
            stmt = self.parse_assert()
        elif kind in ("GLOBAL", "NONLOCAL"):
            if self.function_depth == 0:
                raise self.error(f"{kind.lower()} solo puede usarse dentro de una función", token)
            self.advance()
            names = [self.expect("ID").value]
            while self.current() and self.current().type == "COMMA":
                self.advance()
                names.append(self.expect("ID").value)
            if len(names) != len(set(names)):
                raise self.error(f"Declaración {kind.lower()} repetida", token)
            stmt = (kind.lower(), names)
        elif kind in ("SHOW", "SAY", "WAIT"):
            self.advance()
            self.expect("LPAREN")
            expr = self.parse_expression()
            self.expect("RPAREN")
            stmt = (kind.lower(), expr)
        elif kind == "ASK":
            # ask is also an expression; as a standalone statement its value
            # is simply discarded, matching calls such as input(...).
            stmt = ("expr_stmt", self.parse_expression())
        elif kind == "EXIT":
            stmt = self.parse_exit()
        elif kind == "PASS":
            self.advance()
            stmt = ("pass",)
        elif kind == "LOOP":
            stmt = self.parse_loop()
        elif kind == "UNTIL":
            stmt = self.parse_until()
        elif kind == "UNLESS":
            stmt = self.parse_unless()
        elif kind == "EACH":
            stmt = self.parse_each()
        elif kind == "NUMBER" and self.peek() and self.peek().type == "TIMES":
            stmt = self.parse_times()
        elif kind == "ID":
            stmt = self.parse_expression_statement()
        else:
            raise self.error(f"Declaración no reconocida ({kind})", token)

        self.source_map[id(stmt)] = token
        last = self.tokens[self.pos - 1] if self.pos else token
        self.node_spans[id(stmt)] = self._span_from_tokens(token, last)
        return stmt

    def _at_statement_end(self) -> bool:
        token = self.current()
        return token is None or token.type in {
            "NEWLINE", "END", "ELSE", "ELIF", "RBRACE"
        }

    def _module_name(self) -> str:
        parts = [self.expect("ID").value]
        while self.current() and self.current().type == "DOT":
            self.advance()
            parts.append(self.expect("ID").value)
        return ".".join(parts)

    def parse_import(self):
        self.advance()
        module = self._module_name()
        alias = None
        if self.current() and self.current().type == "AS":
            self.advance()
            alias = self.expect("ID").value
        return ("import", module, alias)

    def parse_from_import(self):
        self.advance()
        module = self._module_name()
        self.expect("IMPORT")
        items = []
        while True:
            name = self.expect("ID").value
            alias = None
            if self.current() and self.current().type == "AS":
                self.advance()
                alias = self.expect("ID").value
            items.append((name, alias))
            if not self.current() or self.current().type != "COMMA":
                break
            self.advance()
            if self.current() and self.current().type == "NEWLINE":
                self.skip_newlines()
        return ("from_import", module, items)

    def parse_let(self):
        self.advance()
        if self.current() and self.current().type in ("LBRACKET", "LPAREN"):
            pattern = self.parse_pattern()
            self.expect("ASSIGN")
            return ("destructure_let", pattern, self.parse_expression())
        name = self.expect("ID").value
        self.expect("ASSIGN")
        return ("let", name, self.parse_expression())

    def parse_pattern(self):
        token = self.current()
        if token is None:
            raise self.error("Se esperaba un patrón de asignación", token)
        if token.type == "ID":
            self.advance()
            pattern = ("pattern_name", token.value)
            self.node_spans[id(pattern)] = self._span_from_tokens(token, token)
            self.source_map[id(pattern)] = token
            return pattern
        if token.type not in ("LBRACKET", "LPAREN"):
            raise self.error("El patrón solo admite nombres dentro de una lista o tupla", token)
        closing_type = "RBRACKET" if token.type == "LBRACKET" else "RPAREN"
        opening = self.advance()
        items = []
        saw_comma = False
        if self.current() and self.current().type != closing_type:
            while True:
                items.append(self.parse_pattern())
                if not self.current() or self.current().type != "COMMA":
                    break
                saw_comma = True
                self.advance()
                if self.current() and self.current().type == closing_type:
                    break
        if not items and closing_type == "RBRACKET":
            raise self.error("El patrón de lista no puede estar vacío", opening)
        if not items:
            raise self.error("El patrón de tupla no puede estar vacío", opening)
        closing = self.expect(closing_type)
        if closing_type == "RPAREN" and len(items) == 1 and not saw_comma:
            # Parentheses around a single name are grouping, like an expression.
            return items[0]
        pattern = ("pattern_list", items)
        self.node_spans[id(pattern)] = self._span_from_tokens(opening, closing)
        self.source_map[id(pattern)] = opening
        return pattern

    def _expression_pattern(self, expression):
        if expression[0] == "var":
            pattern = ("pattern_name", expression[1])
        elif expression[0] in ("list", "tuple") and expression[1]:
            children = [self._expression_pattern(item) for item in expression[1]]
            if any(child is None for child in children):
                return None
            pattern = ("pattern_list", children)
        else:
            return None
        span = self.expression_spans.get(id(expression))
        if span is not None:
            self.node_spans[id(pattern)] = span
        return pattern

    def parse_expression_statement(self):
        token = self.current()
        expr = self.parse_expression()
        if self.current() and self.current().type == "ASSIGN":
            self.advance()
            value = self.parse_expression()
            if expr[0] == "var":
                return ("assign", expr[1], value)
            if expr[0] == "index":
                return ("index_assign", expr[1], expr[2], value)
            if expr[0] == "slice":
                return ("slice_assign", expr[1], expr[2], expr[3], expr[4], value)
            if expr[0] == "attr":
                return ("attr_assign", expr[1], expr[2], value)
            pattern = self._expression_pattern(expr)
            if pattern is not None:
                return ("destructure_assign", pattern, value)
            raise self.error("El destino de asignación debe ser una variable, índice o atributo", token)
        if expr[0] not in ("call", "method", "builtin"):
            raise self.error("Se esperaba una llamada o una asignación", token)
        return ("expr_stmt", expr)

    def _parse_block(self, stop_types):
        if self.block_nesting >= self.MAX_BLOCK_NESTING:
            raise self.error(f"El código supera el anidamiento máximo de {self.MAX_BLOCK_NESTING} bloques")
        self.block_nesting += 1
        try:
            body = []
            self.skip_newlines()
            while self.current() and self.current().type not in stop_types:
                before = self.pos
                body.append(self.parse_statement())
                if self.pos == before:
                    raise self.error("El parser no pudo avanzar")
                if (self.current() and self.current().type != "NEWLINE"
                        and self.current().type not in stop_types):
                    raise self.error("Se esperaba un salto de línea entre declaraciones")
                self.skip_newlines()
            return body
        finally:
            self.block_nesting -= 1

    def parse_if(self):
        self.advance()
        condition = self.parse_expression()
        branches = []
        body = self._parse_block({"ELSE", "ELIF", "END"})
        while self.current() and self.current().type == "ELIF":
            self.advance()
            elif_condition = self.parse_expression()
            elif_body = self._parse_block({"ELSE", "ELIF", "END"})
            branches.append((elif_condition, elif_body))
        else_body = []
        if self.current() and self.current().type == "ELSE":
            self.advance()
            else_body = self._parse_block({"END"})
        self.expect("END")
        return ("if", condition, body, branches, else_body)

    def _parse_loop_body(self):
        self.loop_depth += 1
        try:
            body = self._parse_block({"END"})
            self.expect("END")
            return body
        finally:
            self.loop_depth -= 1

    def parse_repeat(self):
        self.advance()
        times = self.parse_expression()
        return ("repeat", times, self._parse_loop_body())

    def parse_times(self):
        times = self.parse_expression()
        self.expect("TIMES")
        if self.current() and self.current().type == "DO":
            self.advance()
        return ("repeat", times, self._parse_loop_body())

    def parse_while(self):
        self.advance()
        condition = self.parse_expression()
        return ("while", condition, self._parse_loop_body())

    def parse_for(self):
        self.advance()
        var = self.expect("ID").value
        self.expect("IN")
        iterable = self.parse_expression()
        return ("for", var, iterable, self._parse_loop_body())

    def parse_func(self):
        self.advance()
        name = self.expect("ID").value
        self.expect("LPAREN")
        params = []
        defaults = []
        has_default = False
        vararg = None
        if self.current() and self.current().type != "RPAREN":
            while True:
                if self.current() and self.current().type == "MULT":
                    marker = self.advance()
                    if vararg is not None:
                        raise self.error("Una función solo puede declarar un parámetro variádico", marker)
                    param_token = self.expect("ID")
                    param = param_token.value
                    if param in params:
                        raise self.error(f"Parámetro duplicado: {param}", param_token)
                    params.append(param)
                    vararg = param
                    if self.current() and self.current().type == "COMMA":
                        self.advance()
                        if self.current() and self.current().type != "RPAREN":
                            raise self.error("El parámetro variádico debe ser el último", self.current())
                    break
                param_token = self.expect("ID")
                param = param_token.value
                if param in params:
                    raise self.error(f"Parámetro duplicado: {param}")
                params.append(param)
                if self.current() and self.current().type == "ASSIGN":
                    self.advance()
                    defaults.append((param, self.parse_expression()))
                    has_default = True
                elif has_default:
                    raise self.error("Los parámetros obligatorios deben ir antes de los parámetros con valor por defecto",
                                     param_token)
                if not self.current() or self.current().type != "COMMA":
                    break
                self.advance()
                if self.current() and self.current().type == "RPAREN":
                    break
        self.expect("RPAREN")
        previous_loop_depth = self.loop_depth
        self.loop_depth = 0  # break in a nested function cannot escape its caller.
        self.function_depth += 1
        try:
            body = self._parse_block({"END"})
            self.expect("END")
        finally:
            self.function_depth -= 1
            self.loop_depth = previous_loop_depth
        return ("func", name, params, body, defaults, vararg)

    def _parse_call_arguments(self, end_type):
        args = []
        named = set()
        saw_named = False
        if self.current() and self.current().type != end_type:
            while True:
                if (self.current() is not None and self.current().type == "ID" and self.peek()
                        and self.peek().type == "ASSIGN"):
                    name_token = self.advance()
                    if name_token.value in named:
                        raise self.error(f"Argumento con nombre repetido: {name_token.value}", name_token)
                    named.add(name_token.value)
                    saw_named = True
                    self.expect("ASSIGN")
                    value = self.parse_expression()
                    argument = ("named_arg", name_token.value, value)
                    last = self.tokens[self.pos - 1] if self.pos else name_token
                    self.node_spans[id(argument)] = self._span_from_tokens(name_token, last)
                    self.source_map[id(argument)] = name_token
                    args.append(argument)
                else:
                    if saw_named:
                        raise self.error("Los argumentos posicionales deben ir antes de los argumentos con nombre")
                    args.append(self.parse_expression())
                if not self.current() or self.current().type != "COMMA":
                    break
                self.advance()
                if self.current() and self.current().type == end_type:
                    break
        return args

    def parse_exit(self):
        self.advance()
        if self.current() and self.current().type == "LPAREN":
            self.advance()
            code = None if self.current() and self.current().type == "RPAREN" else self.parse_expression()
            self.expect("RPAREN")
        else:
            code = None if self._at_statement_end() else self.parse_expression()
        return ("exit", code)

    def parse_loop(self):
        self.advance()
        return ("loop", self._parse_loop_body())

    def parse_until(self):
        self.advance()
        condition = self.parse_expression()
        return ("until", condition, self._parse_loop_body())

    def parse_unless(self):
        self.advance()
        condition = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block({"END"})
        self.expect("END")
        return ("unless", condition, body)

    def parse_each(self):
        self.advance()
        var = self.expect("ID").value
        self.expect("IN")
        iterable = self.parse_expression()
        return ("each", var, iterable, self._parse_loop_body())

    def parse_assert(self):
        self.advance()
        self.expect("LPAREN")
        condition = self.parse_expression()
        message = None
        if self.current() and self.current().type == "COMMA":
            self.advance()
            message = self.parse_expression()
        self.expect("RPAREN")
        return ("assert", condition, message)

    def parse_expression(self):
        if self.expression_nesting >= self.MAX_EXPRESSION_NESTING:
            raise self.error(f"La expresión supera el anidamiento máximo de {self.MAX_EXPRESSION_NESTING}")
        start = self.current()
        self.expression_nesting += 1
        self.expression_operator_counts.append(0)
        try:
            expression = self.parse_logical_or()
            last = self.tokens[self.pos - 1] if self.pos else start
            span = self._span_from_tokens(start, last)
            if isinstance(expression, tuple) and span is not None:
                self.expression_spans[id(expression)] = span
            return expression
        finally:
            self.expression_operator_counts.pop()
            self.expression_nesting -= 1

    def _binary_node(self, operator, left, right):
        self.expression_operator_counts[-1] += 1
        if self.expression_operator_counts[-1] > self.MAX_BINARY_OPERATORS:
            raise self.error(f"La expresión supera el límite de {self.MAX_BINARY_OPERATORS} operadores")
        return ("binop", operator, left, right)

    def parse_logical_or(self):
        left = self.parse_logical_and()
        while self.current() and self.current().type == "OR":
            self.advance()
            left = self._binary_node("OR", left, self.parse_logical_and())
        return left

    def parse_logical_and(self):
        left = self.parse_comparison()
        while self.current() and self.current().type == "AND":
            self.advance()
            left = self._binary_node("AND", left, self.parse_comparison())
        return left

    def parse_comparison(self):
        left = self.parse_additive()
        while self.current() and self.current().type in ("EQ", "NEQ", "LT", "GT", "LTE", "GTE"):
            op = self.advance().type
            left = self._binary_node(op, left, self.parse_additive())
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current() and self.current().type in ("PLUS", "MINUS"):
            op = self.advance().type
            left = self._binary_node(op, left, self.parse_multiplicative())
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.current() and self.current().type in ("MULT", "DIV", "MOD"):
            op = self.advance().type
            left = self._binary_node(op, left, self.parse_unary())
        return left

    def parse_unary(self):
        if self.current() and self.current().type in ("NOT", "MINUS"):
            if self.unary_nesting >= self.MAX_UNARY_NESTING:
                raise self.error(f"La expresión supera el anidamiento unario máximo de {self.MAX_UNARY_NESTING}")
            op = self.advance().type
            self.unary_nesting += 1
            try:
                return ("unary", op, self.parse_unary())
            finally:
                self.unary_nesting -= 1
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        while self.current():
            if self.current().type == "LBRACKET":
                self.advance()
                lower = None
                if self.current() and self.current().type != "COLON":
                    lower = self.parse_expression()
                if self.current() and self.current().type == "COLON":
                    self.advance()
                    upper = None
                    if self.current() and self.current().type not in ("COLON", "RBRACKET"):
                        upper = self.parse_expression()
                    step = None
                    if self.current() and self.current().type == "COLON":
                        self.advance()
                        if self.current() and self.current().type != "RBRACKET":
                            step = self.parse_expression()
                    self.expect("RBRACKET")
                    expr = ("slice", expr, lower, upper, step)
                    continue
                if lower is None:
                    raise self.error("El índice no puede estar vacío")
                self.expect("RBRACKET")
                expr = ("index", expr, lower)
            elif self.current().type == "DOT":
                self.advance()
                name = self.expect("ID").value
                if self.current() and self.current().type == "LPAREN":
                    self.advance()
                    args = self._parse_call_arguments("RPAREN")
                    self.expect("RPAREN")
                    expr = ("method", expr, name, args)
                else:
                    expr = ("attr", expr, name)
            else:
                break
        return expr

    def parse_primary(self):
        token = self.current()
        if token is None:
            raise self.error("Expresión incompleta al final del archivo", token)
        if token.type == "NUMBER":
            self.advance()
            digits = token.value.replace("_", "")
            if len(digits) > 4096:
                raise self.error("El literal numérico supera el límite de 4096 caracteres", token)
            try:
                value = float(digits) if "." in digits or "e" in digits.lower() else int(digits)
            except (ValueError, OverflowError) as exc:
                raise self.error(f"Literal numérico no válido: {exc}", token) from exc
            if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
                raise self.error("El literal decimal debe ser finito", token)
            return ("number", value)
        if token.type == "STRING":
            self.advance()
            return ("string", ast.literal_eval(token.value))
        if token.type == "BOOL":
            self.advance()
            return ("bool", token.value == "true")
        if token.type == "NULL":
            self.advance()
            return ("null", None)
        if token.type == "LBRACKET":
            return self.parse_list()
        if token.type == "LBRACE":
            return self.parse_dict()
        if token.type in ("INPUT", "ASK", "LEN", "TYPE", "STR", "INT", "FLOAT", "RANGE"):
            return self.parse_builtin()
        if token.type == "ID":
            name = self.advance().value
            if self.current() and self.current().type == "LPAREN":
                self.advance()
                args = self._parse_call_arguments("RPAREN")
                self.expect("RPAREN")
                return ("call", name, args)
            return ("var", name)
        if token.type == "LPAREN":
            self.advance()
            if self.current() and self.current().type == "RPAREN":
                self.advance()
                return ("tuple", [])
            expr = self.parse_expression()
            if self.current() and self.current().type == "COMMA":
                items = [expr]
                while self.current() and self.current().type == "COMMA":
                    self.advance()
                    if self.current() and self.current().type == "RPAREN":
                        break
                    items.append(self.parse_expression())
                self.expect("RPAREN")
                return ("tuple", items)
            self.expect("RPAREN")
            return expr
        raise self.error(f"Token {token.type} no puede iniciar una expresión", token)

    def _parse_arguments(self, end_type: str):
        args = []
        if self.current() and self.current().type != end_type:
            while True:
                args.append(self.parse_expression())
                if not self.current() or self.current().type != "COMMA":
                    break
                self.advance()
                if self.current() and self.current().type == end_type:
                    break
        return args

    def parse_list(self):
        self.expect("LBRACKET")
        elements = self._parse_arguments("RBRACKET")
        self.expect("RBRACKET")
        return ("list", elements)

    def parse_dict(self):
        self.expect("LBRACE")
        pairs = []
        if self.current() and self.current().type != "RBRACE":
            while True:
                key = self.parse_expression()
                self.expect("COLON")
                value = self.parse_expression()
                pairs.append((key, value))
                if not self.current() or self.current().type != "COMMA":
                    break
                self.advance()
                if self.current() and self.current().type == "RBRACE":
                    break
        self.expect("RBRACE")
        return ("dict", pairs)

    def parse_builtin(self):
        name = self.advance().type.lower()
        self.expect("LPAREN")
        args = self._parse_arguments("RPAREN")
        self.expect("RPAREN")
        return ("builtin", name, args)
