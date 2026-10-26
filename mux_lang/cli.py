"""Command-line interface for Mux."""

import argparse
import atexit
import json
import os
import pprint
import sys
import tempfile
import time
import traceback
from pathlib import Path

from . import __version__
from .formatter import format_source
from .interpreter import Interpreter
from .lexer import Lexer, MuxError
from .linter import lint_ast
from .parser import Parser


MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_CONFIG_BYTES = 1024 * 1024


def _strict_json_loads(source):
    def reject_constant(value):
        raise ValueError(f"Constante JSON no estándar: {value}")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Clave JSON duplicada: {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(source, parse_constant=reject_constant, object_pairs_hook=reject_duplicates)
    except RecursionError as exc:
        raise ValueError("El JSON supera el límite de anidamiento") from exc


def _argument_parser():
    parser = argparse.ArgumentParser(prog="mux", description="Ejecuta programas del lenguaje Mux")
    parser.add_argument("file", nargs="?", help="Archivo .mux (usa - para leer de stdin)")
    parser.add_argument("script_args", nargs=argparse.REMAINDER,
                        help="Argumentos para el programa (coloca las opciones de mux antes del archivo)")
    parser.add_argument("--version", action="version", version=f"Mux {__version__}")
    parser.add_argument("--repl", action="store_true", help="Inicia un intérprete interactivo")
    parser.add_argument("--check", action="store_true", help="Comprueba la sintaxis sin ejecutar")
    parser.add_argument("--lint", action="store_true", help="Comprueba sintaxis y advertencias estáticas")
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument("--format", action="store_true", help="Formatea y muestra el código en stdout")
    format_group.add_argument("--write-format", action="store_true", help="Formatea el archivo en el mismo lugar")
    parser.add_argument("--watch", action="store_true", help="Vuelve a ejecutar el archivo cuando cambia")
    parser.add_argument("--watch-interval", type=float, help="Intervalo de observación en segundos")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--tokens", action="store_true", help="Imprime los tokens y termina")
    modes.add_argument("--ast", action="store_true", help="Imprime el AST y termina")
    parser.add_argument("--max-steps", type=int, help="Límite de pasos de ejecución")
    parser.add_argument("--max-call-depth", type=int, help="Límite de llamadas Mux anidadas")
    parser.add_argument("--sandbox-root", help="Restringe acceso a archivos y módulos a esta carpeta")
    parser.add_argument("--config", help="Archivo JSON de configuración de mux")
    parser.add_argument("--diagnostics-format", choices=("text", "json"), help="Formato de diagnósticos")
    parser.add_argument("--time", action="store_true", help="Muestra el tiempo total de ejecución")
    parser.add_argument("--debug", action="store_true", help="Muestra traceback de errores internos")
    return parser


def _default_config_path():
    configured = os.environ.get("MUX_CONFIG")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Mux" / "config.json"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "mux" / "config.json"


def _load_config(filename=None):
    path = Path(filename).expanduser() if filename else _default_config_path()
    if not path.exists():
        return {}
    try:
        if path.stat().st_size > MAX_CONFIG_BYTES:
            raise ValueError("el archivo supera 1 MiB")
        config = _strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise MuxError(f"No se pudo leer la configuración {str(path)!r}: {exc}") from exc
    if not isinstance(config, dict):
        raise MuxError("La configuración de mux debe ser un objeto JSON")
    allowed = {"max_steps", "max_call_depth", "sandbox_root", "diagnostics_format", "watch_interval"}
    unknown = sorted(set(config) - allowed)
    if unknown:
        raise MuxError(f"Claves de configuración desconocidas: {', '.join(unknown)}")
    return config


def _effective_options(args, config):
    max_steps = args.max_steps if args.max_steps is not None else config.get("max_steps")
    max_call_depth = args.max_call_depth if args.max_call_depth is not None else config.get("max_call_depth", 128)
    sandbox_root = args.sandbox_root or config.get("sandbox_root")
    diagnostics_format = args.diagnostics_format or config.get("diagnostics_format", "text")
    watch_interval = args.watch_interval if args.watch_interval is not None else config.get("watch_interval", 0.5)
    if max_steps is not None and (not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps < 1):
        raise MuxError("max_steps debe ser un entero positivo")
    if (not isinstance(max_call_depth, int) or isinstance(max_call_depth, bool)
            or not 1 <= max_call_depth <= 128):
        raise MuxError("max_call_depth debe estar entre 1 y 128")
    if not isinstance(watch_interval, (int, float)) or isinstance(watch_interval, bool) or not 0.1 <= watch_interval <= 60:
        raise MuxError("watch_interval debe estar entre 0.1 y 60 segundos")
    if diagnostics_format not in ("text", "json"):
        raise MuxError("diagnostics_format debe ser text o json")
    if sandbox_root is not None and (not isinstance(sandbox_root, str) or not sandbox_root.strip()):
        raise MuxError("sandbox_root debe ser una ruta de texto no vacía")
    return max_steps, max_call_depth, sandbox_root, diagnostics_format, float(watch_interval)


def _compile(source, filename):
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise MuxError("El archivo Mux supera el límite de 10 MiB", filename)
    tokens = Lexer(source, filename).tokenize()
    parser = Parser(tokens, filename)
    tree = parser.parse()
    return tokens, parser, tree


def _show_error(error, source, filename, debug=False, diagnostics_format="text"):
    if diagnostics_format == "json":
        diagnostic = error.to_dict() if hasattr(error, "to_dict") else {
            "message": str(error), "path": filename, "line": None, "column": None,
        }
        location_source = source
        location_path = getattr(error, "path", None)
        if location_path and location_path not in (filename, "<stdin>", "<repl>"):
            try:
                location_source = Path(location_path).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                location_source = ""
        lines = location_source.splitlines()
        line_number = getattr(error, "line", None)
        diagnostic["source_line"] = lines[line_number - 1] if line_number and 1 <= line_number <= len(lines) else None
        print(json.dumps(diagnostic, ensure_ascii=False), file=sys.stderr)
    else:
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


def _readline_module():
    try:
        import readline
        return readline
    except ImportError:
        try:
            import pyreadline3 as readline
            return readline
        except ImportError:
            return None


def _configure_repl_history():
    readline = _readline_module()
    if readline is None:
        return
    if hasattr(readline, "parse_and_bind"):
        try:
            readline.parse_and_bind("tab: complete")
        except Exception:
            pass
    words = "if elif else end func return break continue repeat while for each import from as let global nonlocal true false null print input len type str int float range".split()
    if hasattr(readline, "set_completer"):
        def complete(text, state):
            matches = [word for word in words if word.startswith(text)]
            return matches[state] if state < len(matches) else None
        readline.set_completer(complete)
    history = _default_config_path().parent / "repl_history"
    try:
        history.parent.mkdir(parents=True, exist_ok=True)
        readline.read_history_file(str(history))
    except (OSError, AttributeError):
        pass
    if hasattr(readline, "set_history_length"):
        readline.set_history_length(1000)
    if hasattr(readline, "write_history_file"):
        atexit.register(lambda: _save_history(readline, history))


def _save_history(readline, history):
    try:
        history.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(str(history))
        if os.name != "nt":
            os.chmod(history, 0o600)
    except (OSError, AttributeError):
        pass


def _run_repl(max_steps=None, max_call_depth=256, sandbox_root=None, debug=False,
              diagnostics_format="text"):
    print(f"Mux {__version__} — escribe :help o :quit", file=sys.stdout)
    _configure_repl_history()
    interpreter = Interpreter(max_steps=max_steps, max_call_depth=max_call_depth,
                              allowed_root=sandbox_root)
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
            if exc.incomplete:
                continue
            _show_error(exc, source, "<repl>", debug, diagnostics_format)
            buffer.clear()
            continue
        interpreter.source_map.update(parser.source_map)
        try:
            exit_code = interpreter.run(tree, "<stdin>")
            buffer.clear()
            if exit_code is not None:
                return exit_code
        except MuxError as exc:
            _show_error(exc, source, "<repl>", debug, diagnostics_format)
            buffer.clear()


def _read_program(filename):
    if filename == "-":
        raw = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
        if len(raw) > MAX_SOURCE_BYTES:
            raise MuxError("La entrada estándar supera el límite de 10 MiB", "<stdin>")
        try:
            return raw.decode("utf-8"), "<stdin>"
        except UnicodeDecodeError as exc:
            raise MuxError(f"La entrada no es UTF-8 válida: {exc}", "<stdin>") from exc
    path = Path(filename).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"el archivo {filename!r} no existe o no es un archivo")
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise MuxError("El archivo Mux supera el límite de 10 MiB", str(path))
    raw = path.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise MuxError("El archivo Mux supera el límite de 10 MiB", str(path))
    try:
        return raw.decode("utf-8"), str(path.resolve())
    except UnicodeDecodeError as exc:
        raise MuxError(f"El archivo no es UTF-8 válido: {exc}", str(path)) from exc


def _print_lint(diagnostics, source_path, diagnostics_format):
    if diagnostics_format == "json":
        print(json.dumps([item.to_dict() for item in diagnostics], ensure_ascii=False))
        return sum(item.severity == "error" for item in diagnostics)
    for item in diagnostics:
        span = item.span
        where = f"{source_path}:{span.start_line}:{span.start_column}: " if span else f"{source_path}: "
        print(f"{where}{item.severity} {item.code}: {item.message}", file=sys.stderr)
    if not diagnostics:
        print("Mux: sin advertencias", file=sys.stdout)
    return sum(item.severity == "error" for item in diagnostics)


def _run_file(args, max_steps, max_call_depth, sandbox_root, diagnostics_format):
    source, display_name = _read_program(args.file)
    tokens, compiled_parser, tree = _compile(source, display_name)
    if args.tokens:
        for token in tokens:
            print(f"{token.line}:{token.column}\t{token.type}\t{token.value!r}")
        return 0
    if args.ast:
        pprint.pprint(tree, sort_dicts=False)
        return 0
    if args.format or args.write_format:
        formatted = format_source(source)
        if args.write_format:
            if args.file == "-":
                raise MuxError("--write-format requiere un archivo, no stdin")
            target = Path(args.file).expanduser().resolve()
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(formatted)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary_name, target)
            finally:
                try:
                    os.unlink(temporary_name)
                except FileNotFoundError:
                    pass
        else:
            sys.stdout.write(formatted)
        return 0
    if args.lint:
        errors = _print_lint(lint_ast(tree), display_name, diagnostics_format)
        return 1 if errors else 0
    if args.check:
        return 0
    interpreter = Interpreter(max_steps=max_steps, max_call_depth=max_call_depth,
                              allowed_root=sandbox_root,
                              source_map=compiled_parser.source_map)
    interpreter.globals["args"] = [value for value in args.script_args if value != "--"]
    started = time.perf_counter()
    exit_code = interpreter.run(tree, display_name)
    if args.time:
        print(f"Mux: {time.perf_counter() - started:.6f} s", file=sys.stderr)
    return exit_code if exit_code is not None else 0


def main(argv=None):
    parser = _argument_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    explicit_script_args = []
    if "--" in raw_argv:
        separator = raw_argv.index("--")
        explicit_script_args = raw_argv[separator + 1:]
        raw_argv = raw_argv[:separator]
    args = parser.parse_args(raw_argv)
    args.script_args.extend(explicit_script_args)
    config = {}
    diagnostics_format = args.diagnostics_format or "text"
    try:
        config = _load_config(args.config)
        max_steps, max_call_depth, sandbox_root, diagnostics_format, watch_interval = _effective_options(args, config)
        if args.repl:
            return _run_repl(max_steps, max_call_depth, sandbox_root, args.debug, diagnostics_format)
        if not args.file:
            parser.error("indica un archivo o usa --repl")
        if args.watch and args.file == "-":
            parser.error("--watch requiere una ruta de archivo")
        if args.watch:
            target = Path(args.file).expanduser()
            previous = None
            try:
                while True:
                    try:
                        stat = target.stat()
                        fingerprint = (stat.st_mtime_ns, stat.st_size)
                        if fingerprint != previous:
                            previous = fingerprint
                            print(f"\nMux: ejecutando {target}", file=sys.stderr)
                            try:
                                result = _run_file(args, max_steps, max_call_depth, sandbox_root, diagnostics_format)
                                if result:
                                    print(f"Mux: código de salida {result}", file=sys.stderr)
                            except MuxError as exc:
                                _show_error(exc, "", str(target), args.debug, diagnostics_format)
                        time.sleep(watch_interval)
                    except FileNotFoundError:
                        time.sleep(watch_interval)
            except KeyboardInterrupt:
                return 130
        return _run_file(args, max_steps, max_call_depth, sandbox_root, diagnostics_format)
    except MuxError as exc:
        diagnostic_format = getattr(args, "diagnostics_format", None) or config.get("diagnostics_format", "text")
        _show_error(exc, "", args.file or "<stdin>", args.debug,
                    diagnostic_format)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"mux: {exc}", file=sys.stderr)
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
