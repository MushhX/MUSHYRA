"""Small source-level debugger used by ``mux --debugger``."""

import reprlib
import sys

from .interpreter import ExitException


class Debugger:
    def __init__(self, input_fn=input, output=None):
        self.input = input_fn
        self.output = output if output is not None else sys.stderr
        self.breakpoints = set()
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
        if not self.stepping and (filename, line) not in self.breakpoints:
            return
        print(f"\n{filename}:{line or '?'}  {statement[0]}", file=self.output)
        while True:
            try:
                command = self.input("mux-debug> ").strip()
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
                if len(parts) == 2 and parts[1].isdigit():
                    self.breakpoints.add((filename, int(parts[1])))
                    print(f"Breakpoint en {filename}:{parts[1]}", file=self.output)
                else:
                    print("Uso: break <línea>", file=self.output)
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
            if verb in ("q", "quit", "exit"):
                raise ExitException(130)
            if verb in ("h", "help", "?"):
                print("step/s, continue/c, break/b <línea>, vars/v, bt, quit/q", file=self.output)
                continue
            print("Comando desconocido; usa help.", file=self.output)
