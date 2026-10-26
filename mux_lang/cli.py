"""Command-line interface for Mux."""

import argparse
import pprint
import sys
import traceback
from pathlib import Path

from . import __version__
from .interpreter import Interpreter
from .lexer import Lexer, MuxError
from .parser import Parser


def _argument_parser():
    parser = argparse.ArgumentParser(prog="mux", description="Ejecuta programas del lenguaje Mux")
    parser.add_argument("file", nargs="?", help="Archivo .mux (usa - para leer de stdin)")
    parser.add_argument("--version", action="version", version=f"Mux {__version__}")
    parser.add_argument("--repl", action="store_true", help="Inicia un intérprete interactivo")
    parser.add_argument("--check", action="store_true", help="Comprueba la sintaxis sin ejecutar")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--tokens", action="store_true", help="Imprime los tokens y termina")
    modes.add_argument("--ast", action="store_true", help="Imprime el AST y termina")
    parser.add_argument("--max-steps", type=int, help="Límite opcional de pasos de ejecución")
    parser.add_argument("--debug", action="store_true", help="Muestra traceback de errores internos")
    return parser


def _compile(source, filename):
    tokens = Lexer(source, filename).tokenize()
    parser = Parser(tokens, filename)
    tree = parser.parse()
    return tokens, parser, tree


def _show_error(error, source, filename, debug=False):
    print(f"mux: {error}", file=sys.stderr)
    if getattr(error, "line", None):
        location_path = getattr(error, "path", None)
        location_source = source
        if location_path and location_path not in (filename, "<stdin>", "<repl>"):
            try:
                location_source = Path(location_path).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                location_source = ""
        lines = location_source.splitlines()
        line_number = error.line
        if 1 <= line_number <= len(lines):
            line = lines[line_number - 1]
            print(f"  {line_number:>4} | {line}", file=sys.stderr)
            if getattr(error, "column", None):
                prefix = line[:error.column - 1]
                pointer = "".join("\t" if char == "\t" else " " for char in prefix)
                print(f"       | {pointer}^", file=sys.stderr)
    if debug and getattr(error, "cause", None):
        traceback.print_exception(type(error.cause), error.cause, error.cause.__traceback__)


def _run_repl(max_steps=None, debug=False):
    print(f"Mux {__version__} — escribe :help o :quit", file=sys.stdout)
    interpreter = Interpreter(max_steps=max_steps)
    buffer = []
    while True:
        prompt = ">>> " if not buffer else "... "
        try:
            line = input(prompt)
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nInterrumpido", file=sys.stdout)
            buffer.clear()
            continue
        command = line.strip()
        if not buffer and command in (":quit", ":q", "exit()"):
            return 0
        if not buffer and command == ":help":
            print("Introduce una declaración Mux; usa :quit para salir. Los bloques se completan con end.")
            continue
        buffer.append(line)
        source = "\n".join(buffer) + "\n"
        try:
            _, parser, tree = _compile(source, "<repl>")
        except MuxError as exc:
            if "fin de archivo" in str(exc).lower() or "final del archivo" in str(exc).lower():
                continue
            _show_error(exc, source, "<repl>", debug)
            buffer.clear()
            continue
        interpreter.source_map.update(parser.source_map)
        try:
            exit_code = interpreter.run(tree, "<stdin>")
            buffer.clear()
            if exit_code is not None:
                return exit_code
        except MuxError as exc:
            _show_error(exc, source, "<repl>", debug)
            buffer.clear()


def main(argv=None):
    parser = _argument_parser()
    args = parser.parse_args(argv)
    if args.max_steps is not None and args.max_steps < 1:
        parser.error("--max-steps debe ser mayor que cero")
    if args.repl:
        return _run_repl(args.max_steps, args.debug)
    if not args.file:
        parser.error("indica un archivo o usa --repl")

    filename = args.file
    try:
        if filename == "-":
            source = sys.stdin.read()
            display_name = "<stdin>"
        else:
            path = Path(filename).expanduser()
            if not path.is_file():
                print(f"mux: el archivo {filename!r} no existe o no es un archivo", file=sys.stderr)
                return 2
            source = path.read_text(encoding="utf-8")
            display_name = str(path.resolve())
        tokens, compiled_parser, tree = _compile(source, display_name)
        if args.tokens:
            for token in tokens:
                print(f"{token.line}:{token.column}\t{token.type}\t{token.value!r}")
            return 0
        if args.ast:
            pprint.pprint(tree, sort_dicts=False)
            return 0
        if args.check:
            return 0
        interpreter = Interpreter(max_steps=args.max_steps, source_map=compiled_parser.source_map)
        exit_code = interpreter.run(tree, display_name)
        return exit_code if exit_code is not None else 0
    except MuxError as exc:
        _show_error(exc, source if "source" in locals() else "", filename, args.debug)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"mux: no se pudo leer {filename!r}: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nmux: ejecución interrumpida", file=sys.stderr)
        return 130
    except Exception as exc:
        if args.debug:
            traceback.print_exc()
        else:
            print(f"mux: error interno: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
