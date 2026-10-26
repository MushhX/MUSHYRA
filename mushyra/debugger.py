"""Small source-level debugger used by ``myr --debugger``."""

import reprlib
import sys

from .interpreter import ExitException
from .lexer import Lexer, MushyraError
from .parser import Parser
from .values import ValueSemantics


class Debugger:
    def __init__(self, input_fn=input, output=None):
        self.input = input_fn
        self.output = output if output is not None else sys.stderr
        self.breakpoints = {}
        self.watches = []
        self.stepping = True
        self._repr = reprlib.Repr()
        self._repr.maxstring = 240
        self._repr.maxother = 240
        self._repr.maxlist = 20
        self._repr.maxdict = 20
        self._repr.maxarray = 20

    @staticmethod
    def _line(statement, interpreter):
        span = getattr(statement, "span", None)
        if span is not None:
            return span.start_line
        token = interpreter.source_map.get(id(statement))
        return token.line if token is not None else None

    def __call__(self, interpreter, statement):
        filename = interpreter.filename
        line = self._line(statement, interpreter)
        key = (filename, line)
        if not self.stepping:
            if key not in self.breakpoints:
                return
            condition = self.breakpoints[key]
            if condition is not None:
                try:
                    if not ValueSemantics.truthy(interpreter.eval_expression(condition)):
                        return
                except Exception as exc:
                    print(f"Breakpoint condicional: {exc}", file=self.output)
        print(f"\n{filename}:{line or '?'}  {statement[0]}", file=self.output)
        self._show_watches(interpreter)
        while True:
            try:
                command = self.input("myr-debug> ").strip()
            except EOFError:
                command = "continue"
            parts = command.split()
            verb = parts[0].lower() if parts else "step"
            if verb in ("s", "step", "n", "next"):
                self.stepping = True
                return
            if verb in ("c", "continue", "r", "run"):
                self.stepping = False
                return
            if verb in ("b", "break"):
                rest = command[len(parts[0]):].strip()
                line_text, separator, condition_text = rest.partition(" if ")
                if not line_text.isdigit() or (separator and not condition_text.strip()):
                    print("Uso: break <línea> [if <expresión MUSHYRA>]", file=self.output)
                    continue
                try:
                    condition = self._parse_expression(condition_text.strip()) if separator else None
                except MushyraError as exc:
                    print(f"Condición no válida: {exc.message}", file=self.output)
                    continue
                target_line = int(line_text)
                self.breakpoints[(filename, target_line)] = condition
                suffix = f" si {condition_text.strip()}" if separator else ""
                print(f"Breakpoint en {filename}:{target_line}{suffix}", file=self.output)
                continue
            if verb in ("w", "watch"):
                expression_text = command[len(parts[0]):].strip()
                if not expression_text:
                    print("Uso: watch <expresión MUSHYRA>", file=self.output)
                    continue
                try:
                    expression = self._parse_expression(expression_text)
                except MushyraError as exc:
                    print(f"Expresión no válida: {exc.message}", file=self.output)
                    continue
                self.watches.append((expression_text, expression))
                print(f"Observación {len(self.watches)} añadida", file=self.output)
                continue
            if verb in ("uw", "unwatch"):
                if len(parts) == 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= len(self.watches):
                    removed = self.watches.pop(int(parts[1]) - 1)
                    print(f"Observación eliminada: {removed[0]}", file=self.output)
                else:
                    print("Uso: unwatch <número>", file=self.output)
                continue
            if verb in ("v", "vars"):
                base = (interpreter.global_scope_stack[-1]
                        if interpreter.global_scope_stack else interpreter.globals)
                values = dict(base)
                for scope in reversed(interpreter.environments[-1] if interpreter.environments else ()):
                    values.update(scope)
                for name, value in sorted(values.items()):
                    rendered = self._repr.repr(value)
                    print(f"{name} = {rendered}", file=self.output)
                continue
            if verb in ("bt", "backtrace"):
                if not interpreter.call_stack:
                    print("(nivel global)", file=self.output)
                for frame in reversed(interpreter.call_stack):
                    print(f"  {frame.name}: llamada en {frame.call_path}:{frame.call_line}; "
                          f"definida en {frame.definition_path}:{frame.definition_line}",
                          file=self.output)
                continue
            if verb in ("m", "modules"):
                if not interpreter.modules:
                    print("(sin módulos cargados)", file=self.output)
                for name, module in sorted(interpreter.modules.items()):
                    exports = ", ".join(sorted(str(item) for item in module))
                    print(f"{name}: {exports or '(sin exportaciones)'}", file=self.output)
                continue
            if verb in ("sc", "scopes"):
                if interpreter.environments:
                    for index, scope in enumerate(interpreter.environments[-1]):
                        label = "local" if index == 0 else f"cierre {index}"
                        print(f"{label}: {', '.join(sorted(scope)) or '(vacío)'}", file=self.output)
                global_scope = (interpreter.global_scope_stack[-1]
                                if interpreter.global_scope_stack else interpreter.globals)
                print(f"global: {', '.join(sorted(global_scope)) or '(vacío)'}", file=self.output)
                continue
            if verb in ("q", "quit", "exit"):
                raise ExitException(130)
            if verb in ("h", "help", "?"):
                print("step/s, continue/c, break/b <línea> [if expr], watch/w <expr>, "
                      "unwatch/uw <n>, vars/v, scopes/sc, modules/m, bt, quit/q", file=self.output)
                continue
            print("Comando desconocido; usa help.", file=self.output)

    @staticmethod
    def _parse_expression(source):
        parser = Parser(Lexer(source, "<depurador>").tokenize(), "<depurador>")
        expression = parser.parse_expression()
        if parser.current() is not None:
            raise parser.error("Hay contenido después de la expresión")
        return expression

    def _show_watches(self, interpreter):
        for index, (source, expression) in enumerate(self.watches, 1):
            try:
                value = interpreter.eval_expression(expression)
                rendered = self._repr.repr(value)
            except Exception as exc:
                rendered = f"<error: {exc}>"
            print(f"watch {index}: {source} = {rendered}", file=self.output)
