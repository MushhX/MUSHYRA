"""A small dependency-free Language Server Protocol implementation for Mux."""

from __future__ import annotations

import bisect
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from .lexer import Lexer, MuxError
from .linter import lint_ast
from .parser import Parser
from .resolver import _statement_expressions, analyze_program


MAX_MESSAGE_BYTES = 16 * 1024 * 1024
MAX_HEADER_BYTES = 8192
KEYWORDS = (
    "let", "if", "elif", "else", "end", "repeat", "while", "for", "each",
    "in", "func", "return", "break", "continue", "global", "nonlocal",
    "assert", "import", "from", "as", "true", "false", "null", "show",
    "say", "ask", "wait", "exit", "loop", "until", "unless", "pass", "print",
    "input", "len", "type", "str", "int", "float", "range", "times", "do",
    "&&", "||", "!",
)


def _uri_path(uri):
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return uri or "<editor>"
    path = unquote(parsed.path)
    if sys.platform == "win32" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return str(Path(path))


def _normalize_source(source):
    return source.replace("\r\n", "\n").replace("\r", "\n")


def _line_offsets(source):
    offsets = [0]
    offsets.extend(index + 1 for index, char in enumerate(source) if char == "\n")
    return offsets


def _position_at(source, line_offsets, offset):
    offset = max(0, min(len(source), offset))
    line = bisect.bisect_right(line_offsets, offset) - 1
    prefix = source[line_offsets[line]:offset]
    character = sum(2 if ord(char) > 0xFFFF else 1 for char in prefix)
    return {"line": line, "character": character}


def _offset_at(source, line_offsets, position):
    line = position.get("line", 0)
    character = position.get("character", 0)
    if not isinstance(line, int) or isinstance(line, bool) or not 0 <= line < len(line_offsets):
        return len(source)
    if not isinstance(character, int) or isinstance(character, bool) or character < 0:
        return line_offsets[line]
    start = line_offsets[line]
    end = line_offsets[line + 1] if line + 1 < len(line_offsets) else len(source)
    offset = start
    units = 0
    while offset < end and units < character:
        width = 2 if ord(source[offset]) > 0xFFFF else 1
        if units + width > character:
            break
        units += width
        offset += 1
    return offset


def _range(source, line_offsets, start, end):
    return {"start": _position_at(source, line_offsets, start),
            "end": _position_at(source, line_offsets, end)}


def _span_range(node, source, line_offsets):
    span = getattr(node, "span", None)
    if span is None:
        return _range(source, line_offsets, 0, 0)
    return _range(source, line_offsets, span.start_offset, span.end_offset)


def _index_tokens(tokens):
    by_name = {}
    for token in tokens:
        if token.type == "ID":
            by_name.setdefault(token.value, []).append(token)
    return {name: ([token.offset for token in matches], matches)
            for name, matches in by_name.items()}


def _find_name_token(token_index, name, start, end):
    entry = token_index.get(name)
    if entry is None:
        return None
    offsets, matches = entry
    index = bisect.bisect_left(offsets, start)
    if index < len(matches) and matches[index].offset < end:
        return matches[index]
    return None


def _token_at(tokens, offset):
    low, high = 0, len(tokens)
    while low < high:
        middle = (low + high) // 2
        if tokens[middle].offset <= offset:
            low = middle + 1
        else:
            high = middle
    if low:
        token = tokens[low - 1]
        if token.type == "ID" and offset <= token.end_offset:
            return token
    return None


def _statement_blocks(statement):
    kind = statement[0]
    if kind == "if":
        yield statement[2]
        for _condition, branch in statement[3]:
            yield branch
        yield statement[4]
    elif kind in ("repeat", "while", "loop", "until", "unless"):
        yield statement[-1]
    elif kind in ("for", "each"):
        yield statement[3]
    elif kind == "func":
        yield statement[3]


def _document_index(source, tokens, tree):
    """Build a lightweight document-local symbol and occurrence index."""
    line_offsets = _line_offsets(source)
    definitions = {}
    occurrences = {}
    symbols = []
    binding_scopes = {}
    token_index = _index_tokens(tokens)

    def add_definition(name, token, kind, statement, scope_id):
        if token is None:
            return
        location = {"uri": None, "range": _range(source, line_offsets,
                                                    token.offset, token.end_offset)}
        definitions.setdefault(name, []).append(location)
        binding_scopes.setdefault(name, set()).add(scope_id)
        span = getattr(statement, "span", None)
        symbol_range = (_range(source, line_offsets, span.start_offset, span.end_offset)
                        if span else location["range"])
        symbols.append({"name": name, "kind": kind, "range": symbol_range,
                        "selectionRange": location["range"]})

    def collect_pattern(pattern, statement, scope_id):
        if pattern[0] == "pattern_name":
            span = getattr(pattern, "span", None)
            if span is not None:
                token = _find_name_token(token_index, pattern[1],
                                         span.start_offset, span.end_offset)
                add_definition(pattern[1], token, 13, statement, scope_id)
        elif pattern[0] == "pattern_list":
            for child in pattern[1]:
                collect_pattern(child, statement, scope_id)
        elif pattern[0] == "pattern_dict":
            for _key, child in pattern[1]:
                collect_pattern(child, statement, scope_id)

    def collect_comprehension_variables(value, statement):
        if isinstance(value, list):
            for child in value:
                collect_comprehension_variables(child, statement)
            return
        if not isinstance(value, tuple) or not value:
            return
        if value[0] == "comp_var":
            span = getattr(value, "span", None)
            if span is not None:
                token = _find_name_token(token_index, value[1], span.start_offset, span.end_offset)
                add_definition(value[1], token, 13, statement, id(value))
            return
        for child in value[1:]:
            collect_comprehension_variables(child, statement)

    def collect_statements(block, scope_id=None):
        for statement in block:
            kind = statement[0]
            span = getattr(statement, "span", None)
            start = span.start_offset if span else 0
            end = span.end_offset if span else len(source)
            if kind in ("let", "assign", "func"):
                name = statement[1]
                token = _find_name_token(token_index, name, start, end)
                add_definition(name, token, 12 if kind == "func" else 13,
                               statement, scope_id)
                if kind == "func" and token is not None:
                    closing = next((candidate for candidate in tokens
                                    if candidate.type == "RPAREN" and token.end_offset <= candidate.offset < end), None)
                    if closing is not None:
                        for param in statement[2]:
                            param_token = _find_name_token(token_index, param,
                                                           token.end_offset, closing.offset)
                            add_definition(param, param_token, 13, statement, id(statement))
            elif kind in ("for", "each"):
                name = statement[1]
                add_definition(name, _find_name_token(token_index, name, start, end),
                               13, statement, scope_id)
            elif kind in ("destructure_let", "destructure_assign"):
                collect_pattern(statement[1], statement, scope_id)
            for expression in _statement_expressions(statement):
                collect_comprehension_variables(expression, statement)
            if kind == "func" and len(statement) > 4:
                for _name, expression in statement[4]:
                    collect_comprehension_variables(expression, statement)
            for child in _statement_blocks(statement):
                collect_statements(child, id(statement) if kind == "func" else scope_id)

    collect_statements(tree)

    def collect_occurrences(value):
        if isinstance(value, list):
            for child in value:
                collect_occurrences(child)
            return
        if not isinstance(value, tuple) or not value:
            return
        kind = value[0]
        if kind == "var":
            span = getattr(value, "span", None)
            if span is not None:
                token = _find_name_token(token_index, value[1], span.start_offset, span.end_offset)
                if token is not None:
                    occurrences.setdefault(value[1], []).append(
                        _range(source, line_offsets, token.offset, token.end_offset))
        elif kind == "call":
            span = getattr(value, "span", None)
            if span is not None:
                token = _find_name_token(token_index, value[1], span.start_offset, span.end_offset)
                if token is not None:
                    occurrences.setdefault(value[1], []).append(
                        _range(source, line_offsets, token.offset, token.end_offset))
        for child in value[1:]:
            collect_occurrences(child)

    collect_occurrences(tree)
    for name, locations in definitions.items():
        occurrences.setdefault(name, []).extend(item["range"] for item in locations)
    return line_offsets, definitions, occurrences, symbols, binding_scopes


def _diagnostic(source, line_offsets, message, code, severity, start=None, end=None):
    if start is None:
        where = {"start": {"line": 0, "character": 0},
                 "end": {"line": 0, "character": 0}}
    else:
        where = _range(source, line_offsets, start, end if end is not None else start + 1)
    return {"range": where, "severity": severity, "code": str(code),
            "source": "Mux", "message": message}


def _compile_diagnostics(uri, source):
    source = _normalize_source(source)
    line_offsets = _line_offsets(source)
    path = _uri_path(uri)
    try:
        tokens = Lexer(source, path).tokenize()
        parser = Parser(tokens, path)
        tree = parser.parse()
    except MuxError as exc:
        offset = None
        if exc.line is not None and exc.column is not None:
            line = max(0, min(len(line_offsets) - 1, exc.line - 1))
            offset = line_offsets[line] + max(0, exc.column - 1)
        return [_diagnostic(source, line_offsets, exc.message, exc.code, 1,
                            offset, offset + 1 if offset is not None else None)], None

    diagnostics = []
    for item in lint_ast(tree):
        if item.severity == "error":
            continue
        span = item.span
        diagnostics.append(_diagnostic(
            source, line_offsets, item.message, item.code, 2,
            span.start_offset if span else None,
            span.end_offset if span else None,
        ))
    try:
        analyze_program(tree, path, initial_names=("args",))
    except MuxError as exc:
        offset = None
        if exc.line is not None and exc.column is not None:
            line = max(0, min(len(line_offsets) - 1, exc.line - 1))
            offset = line_offsets[line] + max(0, exc.column - 1)
        diagnostic = _diagnostic(source, line_offsets, exc.message, exc.code, 1,
                                 offset, offset + 1 if offset is not None else None)
        diagnostics.append(diagnostic)
    return diagnostics, (tokens, tree)


class MuxLanguageServer:
    def __init__(self, reader=None, writer=None):
        self.reader = reader if reader is not None else sys.stdin.buffer
        self.writer = writer if writer is not None else sys.stdout.buffer
        self.documents = {}
        self.shutdown_requested = False
        self.exit_requested = False

    def _read_message(self):
        headers = {}
        total = 0
        while True:
            line = self.reader.readline(MAX_HEADER_BYTES + 1)
            if not line:
                return None
            total += len(line)
            if total > MAX_HEADER_BYTES:
                raise ValueError("LSP header exceeds the size limit")
            if line in (b"\r\n", b"\n"):
                break
            if b":" not in line:
                raise ValueError("Malformed LSP header")
            name, value = line.decode("ascii").split(":", 1)
            headers[name.strip().lower()] = value.strip()
        length_text = headers.get("content-length")
        if length_text is None:
            raise ValueError("LSP message is missing Content-Length")
        length = int(length_text)
        if not 0 <= length <= MAX_MESSAGE_BYTES:
            raise ValueError("LSP message exceeds the size limit")
        parts = []
        remaining = length
        while remaining:
            chunk = self.reader.read(remaining)
            if not chunk:
                break
            parts.append(chunk)
            remaining -= len(chunk)
        body = b"".join(parts)
        if len(body) != length:
            raise EOFError("Incomplete LSP message")
        return json.loads(body.decode("utf-8"))

    def _write_message(self, message):
        body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.writer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
        self.writer.write(body)
        self.writer.flush()

    @staticmethod
    def _error(request_id, code, message):
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": code, "message": message}}

    def _publish(self, uri, source):
        diagnostics, compiled = _compile_diagnostics(uri, source)
        document = self.documents[uri]
        document["compiled"] = compiled
        document["index"] = None
        self._write_message({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                             "params": {"uri": uri, "version": document.get("version"),
                                        "diagnostics": diagnostics}})

    def _document(self, uri):
        return self.documents.get(uri)

    def _index(self, uri):
        document = self._document(uri)
        if document is None:
            return None
        if document.get("compiled") is None:
            _, compiled = _compile_diagnostics(uri, document["text"])
            document["compiled"] = compiled
        compiled = document.get("compiled")
        if compiled is None:
            return None
        tokens, tree = compiled
        if document.get("index") is None:
            source = _normalize_source(document["text"])
            document["index"] = _document_index(source, tokens, tree)
        return (document, tokens, tree,
                document["index"])

    def _definition(self, uri, position):
        indexed = self._index(uri)
        if indexed is None:
            return None
        document, tokens, _tree, (line_offsets, definitions, _occurrences, _symbols, _scopes) = indexed
        cursor = _offset_at(_normalize_source(document["text"]), line_offsets, position)
        token = _token_at(tokens, cursor)
        if token is None:
            return None
        candidates = definitions.get(token.value, [])
        if not candidates:
            return None
        candidate = min(candidates, key=lambda item: abs(
            _offset_at(_normalize_source(document["text"]), line_offsets,
                       item["range"]["start"]) - cursor))
        return {"uri": uri, "range": candidate["range"]}

    def _references(self, uri, position, include_declaration=True):
        indexed = self._index(uri)
        if indexed is None:
            return []
        document, tokens, _tree, (line_offsets, definitions, occurrences, _symbols, _scopes) = indexed
        cursor = _offset_at(_normalize_source(document["text"]), line_offsets, position)
        token = _token_at(tokens, cursor)
        if token is None:
            return []
        ranges = list(occurrences.get(token.value, ()))
        if not include_declaration:
            declaration_ranges = {
                (item["range"]["start"]["line"], item["range"]["start"]["character"],
                 item["range"]["end"]["line"], item["range"]["end"]["character"])
                for item in definitions.get(token.value, ())
            }
            ranges = [item for item in ranges if (
                item["start"]["line"], item["start"]["character"],
                item["end"]["line"], item["end"]["character"]) not in declaration_ranges]
        return [{"uri": uri, "range": item} for item in ranges]

    def _completion(self, uri, position):
        indexed = self._index(uri)
        names = set(KEYWORDS)
        if indexed is not None:
            _document, _tokens, _tree, (_offsets, definitions, _occurrences, _symbols,
                                        _scopes) = indexed
            names.update(definitions)
        return [{"label": name, "kind": 14 if name in KEYWORDS else 6}
                for name in sorted(names)]

    def _dispatch(self, method, params):
        if method == "initialize":
            return {"capabilities": {
                "textDocumentSync": {"openClose": True, "change": 1, "save": {"includeText": True}},
                "completionProvider": {"resolveProvider": False, "triggerCharacters": ["."]},
                "definitionProvider": True,
                "referencesProvider": True,
                "renameProvider": True,
                "documentSymbolProvider": True,
                "workspaceSymbolProvider": True,
            }, "serverInfo": {"name": "Mux Language Server", "version": "1.0"}}
        if method == "initialized" or method == "$/setTrace":
            return None
        if method == "shutdown":
            self.shutdown_requested = True
            return None
        if method == "exit":
            self.exit_requested = True
            return None
        if method == "textDocument/didOpen":
            item = params["textDocument"]
            uri = item["uri"]
            self.documents[uri] = {"text": item.get("text", ""),
                                   "version": item.get("version")}
            self._publish(uri, self.documents[uri]["text"])
            return None
        if method == "textDocument/didChange":
            item = params["textDocument"]
            document = self.documents.get(item["uri"])
            if document is None:
                return None
            changes = params.get("contentChanges", [])
            # Full document synchronization is advertised; use the last full change.
            if changes and "text" in changes[-1]:
                document["text"] = changes[-1]["text"]
                document["version"] = item.get("version")
                document["compiled"] = None
                document["index"] = None
                self._publish(item["uri"], document["text"])
            return None
        if method == "textDocument/didSave":
            item = params["textDocument"]
            if item["uri"] in self.documents:
                text = params.get("text", self.documents[item["uri"]]["text"])
                self.documents[item["uri"]]["text"] = text
                self.documents[item["uri"]]["compiled"] = None
                self.documents[item["uri"]]["index"] = None
                self._publish(item["uri"], text)
            return None
        if method == "textDocument/didClose":
            uri = params["textDocument"]["uri"]
            self.documents.pop(uri, None)
            self._write_message({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                                 "params": {"uri": uri, "diagnostics": []}})
            return None
        if method == "textDocument/completion":
            item = params["textDocument"]
            return {"isIncomplete": False,
                    "items": self._completion(item["uri"], params.get("position", {}))}
        if method == "textDocument/definition":
            item = params["textDocument"]
            return self._definition(item["uri"], params.get("position", {}))
        if method == "textDocument/references":
            item = params["textDocument"]
            context = params.get("context", {})
            return self._references(item["uri"], params.get("position", {}),
                                    context.get("includeDeclaration", True))
        if method == "textDocument/rename":
            item = params["textDocument"]
            return self._rename(item["uri"], params.get("position", {}), params.get("newName", ""))
        if method == "textDocument/documentSymbol":
            item = params["textDocument"]
            indexed = self._index(item["uri"])
            if indexed is None:
                return []
            return indexed[3][3]
        if method == "workspace/symbol":
            query = params.get("query", "")
            if not isinstance(query, str):
                return []
            query = query.casefold()
            result = []
            for uri in self.documents:
                indexed = self._index(uri)
                if indexed is None:
                    continue
                for symbol in indexed[3][3]:
                    if query in symbol["name"].casefold():
                        result.append({
                            "name": symbol["name"], "kind": symbol["kind"],
                            "location": {"uri": uri, "range": symbol["selectionRange"]},
                        })
            return result
        if method == "textDocument/hover":
            item = params["textDocument"]
            definition = self._definition(item["uri"], params.get("position", {}))
            if definition is None:
                return None
            return {"contents": {"kind": "markdown",
                                  "value": "Declaración en el documento Mux abierto."},
                    "range": definition["range"]}
        return NotImplemented

    def _rename(self, uri, position, new_name):
        indexed = self._index(uri)
        if indexed is None or not isinstance(new_name, str):
            return None
        document, tokens, _tree, (line_offsets, definitions, _occurrences, _symbols,
                                  binding_scopes) = indexed
        cursor = _offset_at(_normalize_source(document["text"]), line_offsets, position)
        token = _token_at(tokens, cursor)
        if token is None:
            return None
        try:
            parsed_name = [item for item in Lexer(new_name).tokenize()
                           if item.type != "NEWLINE"]
        except MuxError:
            return None
        if (len(parsed_name) != 1 or parsed_name[0].type != "ID"
                or parsed_name[0].offset != 0 or parsed_name[0].end_offset != len(new_name)):
            return None
        new_name = parsed_name[0].value
        # Be conservative around shadowed names: this document-local index cannot
        # prove which binding every reference targets when a name is redeclared.
        current_scopes = binding_scopes.get(token.value, set())
        if len(current_scopes) != 1:
            return None
        target_scopes = binding_scopes.get(new_name, set())
        if new_name != token.value and current_scopes.intersection(target_scopes):
            return None
        locations = self._references(uri, position, include_declaration=True)
        return {"changes": {uri: [{"range": item["range"], "newText": new_name}
                                   for item in locations]}}

    def serve(self):
        while not self.exit_requested:
            try:
                message = self._read_message()
            except EOFError:
                break
            except Exception as exc:
                print(f"Mux LSP: {exc}", file=sys.stderr)
                break
            if message is None:
                break
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                self._write_message(self._error(message.get("id") if isinstance(message, dict) else None,
                                                 -32600, "Invalid Request"))
                continue
            method = message.get("method")
            request_id = message.get("id")
            try:
                result = self._dispatch(method, message.get("params") or {})
                if request_id is not None:
                    if result is NotImplemented:
                        self._write_message(self._error(request_id, -32601,
                                                         f"Method not found: {method}"))
                    else:
                        self._write_message({"jsonrpc": "2.0", "id": request_id,
                                             "result": result})
            except Exception as exc:
                if request_id is not None:
                    self._write_message(self._error(request_id, -32603, "Internal error"))
                print(f"Mux LSP ({method}): {exc}", file=sys.stderr)
        return 0


def run():
    return MuxLanguageServer().serve()
