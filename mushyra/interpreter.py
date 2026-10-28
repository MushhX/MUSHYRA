"""MUSHYRA tree-walking interpreter."""

import math
import os
import sys
import threading
import time
import hashlib
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .lexer import Lexer, MushyraError
from .parser import Parser
from .ast_nodes import ASTNode
from .resolver import FunctionScope, analyze_program
from .values import ValueSemantics


MAX_COLLECTION_ITEMS = 1_000_000
MAX_STRING_CHARACTERS = 10_000_000
MAX_INTEGER_BITS = 1_000_000
MAX_MODULE_SOURCE_BYTES = 10 * 1024 * 1024
MAX_OUTPUT_BYTES = 10 * 1024 * 1024
MAX_RUNTIME_ALLOCATION_BYTES = 64 * 1024 * 1024
# Cache accounting is weighted by source size; the retained AST heap is larger.
MAX_MODULE_AST_CACHE_SOURCE_BYTES = 32 * 1024 * 1024
MAX_WAIT_SECONDS = 300
DEFAULT_MAX_CALL_DEPTH = 128
MAX_CALL_DEPTH = 128

_MODULE_AST_CACHE = OrderedDict()
_MODULE_AST_CACHE_BYTES = 0
_MODULE_AST_CACHE_LOCK = threading.RLock()


def _parse_module_cached(source_bytes, filename):
    global _MODULE_AST_CACHE_BYTES
    source_hash = hashlib.sha256(source_bytes).digest()
    cache_key = (str(filename), source_hash)
    with _MODULE_AST_CACHE_LOCK:
        cached = _MODULE_AST_CACHE.get(cache_key)
        if cached is not None:
            _MODULE_AST_CACHE.move_to_end(cache_key)
            return cached[0], cached[1]
    try:
        source = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MushyraError(f"El módulo no es UTF-8 válido: {exc}", str(filename)) from exc
    tokens = Lexer(source, str(filename)).tokenize()
    parser = Parser(tokens, str(filename))
    tree = parser.parse()
    weight = len(source_bytes)
    if weight <= MAX_MODULE_AST_CACHE_SOURCE_BYTES:
        with _MODULE_AST_CACHE_LOCK:
            previous = _MODULE_AST_CACHE.pop(cache_key, None)
            if previous is not None:
                _MODULE_AST_CACHE_BYTES -= previous[2]
            _MODULE_AST_CACHE[cache_key] = (tree, parser.source_map, weight)
            _MODULE_AST_CACHE_BYTES += weight
            while _MODULE_AST_CACHE_BYTES > MAX_MODULE_AST_CACHE_SOURCE_BYTES:
                _, evicted = _MODULE_AST_CACHE.popitem(last=False)
                _MODULE_AST_CACHE_BYTES -= evicted[2]
    return tree, parser.source_map


@dataclass
class ExecutionBudget:
    max_steps: Optional[int]
    steps: int = 0
    max_output_bytes: Optional[int] = MAX_OUTPUT_BYTES
    output_bytes: int = 0
    max_allocation_bytes: Optional[int] = MAX_RUNTIME_ALLOCATION_BYTES
    allocated_bytes: int = 0
    max_duration_seconds: Optional[float] = None
    deadline: Optional[float] = None
    lock: Any = field(default_factory=threading.RLock, repr=False)


class BudgetedWriter:
    """Text writer that enforces a shared UTF-8 output budget."""

    def __init__(self, target, budget):
        self.target = target
        self.budget = budget
        self._myr_budget = budget

    def write(self, text):
        encoded_size = len(str(text).encode("utf-8", errors="replace"))
        limit = self.budget.max_output_bytes
        with self.budget.lock:
            if limit is not None and self.budget.output_bytes + encoded_size > limit:
                raise MushyraError(f"La salida supera el límite de {limit} bytes")
            result = self.target.write(text)
            self.budget.output_bytes += encoded_size
        return result

    def __getattr__(self, name):
        return getattr(self.target, name)


@dataclass(frozen=True)
class CallFrame:
    name: str
    call_path: str
    call_line: Any
    call_column: Any
    definition_path: str
    definition_line: Any
    definition_column: Any

    def format(self):
        call_site = f"{self.call_path}:{self.call_line}"
        if self.call_column is not None:
            call_site += f":{self.call_column}"
        definition = f"{self.definition_path}:{self.definition_line}"
        if self.definition_column is not None:
            definition += f":{self.definition_column}"
        return f"función {self.name}, llamada desde {call_site} (definida en {definition})"


@dataclass(frozen=True)
class NamedArgument:
    name: str
    value: Any


class BreakException(Exception):
    pass


class ContinueException(Exception):
    pass


class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


class ThrownException(Exception):
    """Internal control signal carrying a value raised by MUSHYRA code."""

    def __init__(self, value, path, line, column, contexts):
        self.value = value
        self.path = path
        self.line = line
        self.column = column
        self.contexts = tuple(contexts)


class ExitException(Exception):
    def __init__(self, code: int):
        self.code = code


class ModuleNamespace(dict):
    """A module's exported names, distinct from ordinary MUSHYRA dictionaries."""


@dataclass(eq=False)
class FunctionValue:
    name: str
    params: List[str]
    body: List[Any]
    closure: Tuple[Dict[str, Any], ...]
    globals: Dict[str, Any]
    source_map: Optional[Dict[int, Any]] = None
    filename: str = "<stdin>"
    current_dir: str = "."
    local_names: frozenset = frozenset()
    global_names: frozenset = frozenset()
    nonlocal_names: frozenset = frozenset()
    free_bindings: Dict[str, int] = field(default_factory=dict)
    resolved_globals: frozenset = frozenset()
    definition_span: Any = None
    default_values: Dict[str, Any] = field(default_factory=dict)
    vararg_name: Optional[str] = None

    def __repr__(self):
        return f"<MUSHYRA function {self.name}>"


class Interpreter:
    """Evaluate MUSHYRA ASTs with lexical function scope and embeddable IO."""

    DICT_METHODS = frozenset({"get", "keys", "values", "items", "update"})

    def __init__(self, output=None, input_fn=None, max_steps: Optional[int] = None,
                 source_map=None, module_cache=None, budget=None,
                 max_call_depth: int = DEFAULT_MAX_CALL_DEPTH,
                 cancel_event=None, allowed_root=None, call_stack=None,
                 max_output_bytes: Optional[int] = MAX_OUTPUT_BYTES,
                 max_allocation_bytes: Optional[int] = MAX_RUNTIME_ALLOCATION_BYTES,
                 timeout_seconds: Optional[float] = None, sandbox_mode: bool = False,
                 debugger_hook=None):
        self.globals: Dict[str, Any] = {}
        self.environments: List[Tuple[Dict[str, Any], ...]] = []
        self.declarations: List[Tuple[set, set]] = []
        self.global_scope_stack: List[Dict[str, Any]] = []
        self.modules = module_cache if module_cache is not None else {}
        self.current_dir = os.getcwd()
        self.filename = "<stdin>"
        self.output_target = output if output is not None else sys.stdout
        self.input = input_fn if input_fn is not None else input
        if (max_steps is not None and
                (not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps < 1)):
            raise ValueError("max_steps debe ser un entero positivo o None")
        if (not isinstance(max_call_depth, int) or isinstance(max_call_depth, bool)
                or not 1 <= max_call_depth <= MAX_CALL_DEPTH):
            raise ValueError(f"max_call_depth debe estar entre 1 y {MAX_CALL_DEPTH}")
        for name, value in (("max_output_bytes", max_output_bytes),
                            ("max_allocation_bytes", max_allocation_bytes)):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
                raise ValueError(f"{name} debe ser un entero positivo o None")
        if timeout_seconds is not None and (
                not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool)
                or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
            raise ValueError("timeout_seconds debe ser finito y positivo o None")
        if not isinstance(sandbox_mode, bool):
            raise ValueError("sandbox_mode debe ser boolean")
        self.budget = budget if budget is not None else ExecutionBudget(
            max_steps, max_output_bytes=max_output_bytes,
            max_allocation_bytes=max_allocation_bytes,
            max_duration_seconds=timeout_seconds,
        )
        self._owns_budget = budget is None
        self.output = (self.output_target if getattr(self.output_target, "_myr_budget", None) is self.budget
                       else BudgetedWriter(self.output_target, self.budget))
        self.max_steps = self.budget.max_steps
        self.max_call_depth = max_call_depth
        self.cancel_event = cancel_event
        self.sandbox_mode = sandbox_mode
        self._root_explicit = allowed_root is not None
        self.allowed_root = (Path(allowed_root).expanduser().resolve() if allowed_root is not None
                             else Path.cwd().resolve() if self.sandbox_mode else None)
        self.debugger_hook = debugger_hook
        self.source_map = source_map or {}
        self.current_location = None
        self.call_stack = call_stack if call_stack is not None else []
        self.local_names_stack = []
        self.free_bindings_stack = []
        self.resolved_globals_stack = []
        self.function_scopes = {}

    def run(self, ast: List[Any], filename: str = "<stdin>"):
        self.filename = filename
        self.current_dir = os.path.dirname(os.path.abspath(filename)) if filename != "<stdin>" else os.getcwd()
        if self.sandbox_mode and not self._root_explicit:
            self.allowed_root = Path(self.current_dir).resolve()
        if self._owns_budget:
            self.budget.steps = 0
            self.budget.deadline = (time.monotonic() + self.budget.max_duration_seconds
                                    if self.budget.max_duration_seconds is not None else None)
        self.function_scopes = analyze_program(ast, filename, self.globals.keys())
        try:
            for statement in ast:
                self.eval_statement(statement)
        except ExitException as exc:
            return exc.code
        except BreakException as exc:
            raise self._located_error("break fuera de un bucle") from exc
        except ContinueException as exc:
            raise self._located_error("continue fuera de un bucle") from exc
        except ReturnException as exc:
            raise self._located_error("return fuera de una función") from exc
        except ThrownException as exc:
            error = MushyraError(
                self._exception_message(exc.value), exc.path, exc.line, exc.column,
                cause=exc, code="MYR3001",
            )
            for context in exc.contexts:
                error.add_context(context)
            raise error from exc
        return None

    def _exception_message(self, value):
        if isinstance(value, str):
            detail = value[:2048]
            if len(value) > len(detail):
                detail += "…"
        elif value is None or isinstance(value, bool) or isinstance(value, float):
            detail = self._stringify(value)
        elif isinstance(value, int) and value.bit_length() <= 4096:
            detail = str(value)
        else:
            detail = f"<{self._type_name(value)}>"
        return f"Excepción no capturada: {detail}"

    def _located_error(self, message, cause=None):
        token = self.current_location
        return MushyraError(
            message,
            path=self.filename,
            line=token.line if token else None,
            column=token.column if token else None,
            cause=cause,
            code="MYR3001",
        )

    def _tick(self):
        self.budget.steps += 1
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise self._located_error("Ejecución cancelada")
        if self.budget.deadline is not None and time.monotonic() >= self.budget.deadline:
            raise self._located_error("Se agotó el tiempo máximo de ejecución")
        if self.max_steps is not None and self.budget.steps > self.max_steps:
            raise self._located_error(f"Se alcanzó el límite de {self.max_steps} pasos de ejecución")

    def bounded_timeout(self, requested):
        """Cap a blocking native-operation timeout by the remaining run budget."""
        if isinstance(requested, bool):
            raise self._located_error("El timeout debe ser un número")
        try:
            requested = float(requested)
        except (TypeError, ValueError, OverflowError) as exc:
            raise self._located_error("El timeout debe ser un número", exc) from exc
        if self.budget.deadline is None:
            return requested
        remaining = self.budget.deadline - time.monotonic()
        if remaining <= 0:
            self._tick()
        return max(0.001, min(float(requested), remaining))

    def _charge_allocation(self, amount):
        limit = self.budget.max_allocation_bytes
        if amount <= 0 or limit is None:
            return
        with self.budget.lock:
            self.budget.allocated_bytes += amount
            if self.budget.allocated_bytes > limit:
                raise self._located_error(f"La memoria asignada supera el presupuesto de {limit} bytes")

    @classmethod
    def _estimate_value_allocation(cls, value, seen=None, check_step=None):
        if check_step is not None:
            check_step()
        seen = seen if seen is not None else set()
        identity = id(value)
        if identity in seen:
            return 0
        seen.add(identity)
        if isinstance(value, str):
            return 49 + 4 * len(value)
        if isinstance(value, list):
            return 64 + 8 * len(value) + sum(
                cls._estimate_value_allocation(item, seen, check_step) for item in value
            )
        if isinstance(value, tuple):
            return 48 + 8 * len(value) + sum(
                cls._estimate_value_allocation(item, seen, check_step) for item in value
            )
        if isinstance(value, dict):
            return 128 + 64 * len(value) + sum(
                cls._estimate_value_allocation(key, seen, check_step)
                + cls._estimate_value_allocation(item, seen, check_step)
                for key, item in value.items()
            )
        if isinstance(value, int) and not isinstance(value, bool):
            return 28 + max(1, (value.bit_length() + 7) // 8)
        if isinstance(value, float):
            return 24
        if value is None or isinstance(value, bool):
            return 8
        return 64

    def _check_native_module(self, module):
        if self.sandbox_mode and module not in {
                "math", "random", "sequence", "path", "strings", "json", "toml", "csv",
                "regex", "time", "console", "filesystem", "database"}:
            raise self._located_error(f"El módulo nativo {module!r} está deshabilitado en modo sandbox")

    @property
    def steps(self):
        return self.budget.steps

    def resolve_path(self, value):
        try:
            path = Path(str(value)).expanduser()
            if not path.is_absolute():
                path = Path(self.current_dir) / path
            resolved = path.resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise MushyraError(f"No se pudo resolver la ruta {str(value)!r}: {exc}") from exc
        if self.allowed_root is not None:
            try:
                resolved.relative_to(self.allowed_root)
            except ValueError as exc:
                raise MushyraError(f"La ruta {str(value)!r} queda fuera del directorio permitido") from exc
        return resolved

    def sleep(self, seconds):
        deadline = time.monotonic() + self.bounded_timeout(seconds)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._tick()
                return
            if self.cancel_event is not None and self.cancel_event.is_set():
                raise self._located_error("Ejecución cancelada durante la espera")
            time.sleep(min(remaining, 0.1))

    def _read_input(self, prompt):
        self._tick()
        if self.input is not input:
            result = self.input(prompt)
            self._tick()
            return result
        if os.name == "nt" and getattr(sys.stdin, "isatty", lambda: False)():
            try:
                import msvcrt
                print(prompt, end="", file=self.output, flush=True)
                chars = []
                while True:
                    self._tick()
                    if msvcrt.kbhit():
                        char = msvcrt.getwch()
                        if char in ("\r", "\n"):
                            print(file=self.output)
                            return "".join(chars)
                        if char == "\x03":
                            raise KeyboardInterrupt
                        if char == "\b":
                            if chars:
                                chars.pop()
                                print("\b \b", end="", file=self.output, flush=True)
                            continue
                        if char in ("\x00", "\xe0"):
                            msvcrt.getwch()
                            continue
                        chars.append(char)
                        print(char, end="", file=self.output, flush=True)
                    else:
                        time.sleep(0.05)
            except ImportError:
                pass
        else:
            try:
                import select
                if sys.stdin.isatty():
                    print(prompt, end="", file=self.output, flush=True)
                    while True:
                        self._tick()
                        readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if readable:
                            line = sys.stdin.readline()
                            if line == "":
                                raise EOFError
                            return line.rstrip("\r\n")
            except (ImportError, OSError, ValueError):
                pass
        # Custom callbacks and non-selectable streams are cooperative: cancellation
        # is observed immediately before and after their synchronous call.
        result = self.input(prompt)
        self._tick()
        return result

    def eval_statement(self, stmt):
        if not stmt:
            return None
        prior_location = self.current_location
        self.current_location = getattr(stmt, "span", None) or self.source_map.get(id(stmt), prior_location)
        try:
            self._tick()
            if self.debugger_hook is not None:
                self.debugger_hook(self, stmt)
                self._tick()
            return self._eval_statement(stmt)
        except MushyraError as exc:
            if exc.code == "MYR000":
                exc.code = "MYR3001"
            span = getattr(stmt, "span", None)
            token = self.source_map.get(id(stmt))
            if span is not None:
                exc.set_location(self.filename, span.start_line, span.start_column)
            elif token:
                exc.set_location(self.filename, token.line, token.column)
            if exc.cause is None and exc.__cause__ is not None:
                exc.cause = exc.__cause__
            if self.call_stack:
                exc.add_context(self.call_stack[-1].format())
            raise
        except (TypeError, ValueError, IndexError, KeyError, ZeroDivisionError, OverflowError) as exc:
            error = self._located_error(f"Error de ejecución: {exc}", exc)
            if self.call_stack:
                error.add_context(self.call_stack[-1].format())
            raise error from exc
        except RecursionError as exc:
            error = self._located_error("Se superó el límite seguro de profundidad de evaluación", exc)
            if self.call_stack:
                error.add_context(self.call_stack[-1].format())
            raise error from exc
        except (BreakException, ContinueException, ReturnException, ExitException,
                ThrownException):
            raise
        except Exception as exc:
            error = self._located_error(f"Error de ejecución: {exc}", exc)
            if self.call_stack:
                error.add_context(self.call_stack[-1].format())
            raise error from exc
        finally:
            self.current_location = prior_location

    def _eval_statement(self, stmt):
        kind = stmt[0]

        if kind == "import":
            _, module, alias = stmt
            self.import_module(module, alias)
        elif kind == "from_import":
            _, module, items = stmt
            self.from_import_module(module, items)
        elif kind in ("let", "assign"):
            _, name, expression = stmt
            self.set_var(name, self.eval_expression(expression))
        elif kind in ("destructure_let", "destructure_assign"):
            _, pattern, expression = stmt
            value = self.eval_expression(expression)
            bindings = []
            self._collect_pattern_bindings(pattern, value, bindings)
            for name, item in bindings:
                self.set_var(name, item)
        elif kind == "index_assign":
            _, obj_expr, index_expr, value_expr = stmt
            obj = self.eval_expression(obj_expr)
            index = self.eval_expression(index_expr)
            value = self.eval_expression(value_expr)
            if isinstance(obj, list):
                self._check_index(index)
                if index < 0:
                    index += len(obj)
                if index < 0 or index >= len(obj):
                    raise MushyraError(f"Índice {index} fuera de rango")
                obj[index] = self._guard_value(value)
            elif isinstance(obj, dict):
                self._set_dict_item(obj, index, value)
            else:
                raise MushyraError("Solo se puede asignar un índice de lista o diccionario")
        elif kind == "slice_assign":
            _, obj_expr, lower_expr, upper_expr, step_expr, value_expr = stmt
            obj = self.eval_expression(obj_expr)
            if not isinstance(obj, list):
                raise MushyraError("Solo se pueden asignar slices de listas")
            bounds = [self._eval_slice_bound(self.eval_expression(item) if item is not None else None)
                      for item in (lower_expr, upper_expr, step_expr)]
            value = self.eval_expression(value_expr)
            if not isinstance(value, (list, tuple, str, range)):
                raise MushyraError("El valor asignado a un slice debe ser una secuencia")
            try:
                replacement_size = len(value)
            except OverflowError as exc:
                raise MushyraError("La secuencia asignada supera el límite permitido") from exc
            if replacement_size > MAX_COLLECTION_ITEMS:
                raise MushyraError(f"Una lista no puede superar {MAX_COLLECTION_ITEMS} elementos")
            try:
                selected = range(*slice(*bounds).indices(len(obj)))
                target_size = len(selected)
            except ValueError as exc:
                raise MushyraError("El paso de un slice no puede ser cero") from exc
            new_size = len(obj) - target_size + replacement_size
            if new_size > MAX_COLLECTION_ITEMS:
                raise MushyraError(f"Una lista no puede superar {MAX_COLLECTION_ITEMS} elementos")
            self._charge_allocation(8 * max(0, new_size - len(obj)))
            if isinstance(value, list):
                replacement = value
            else:
                self._charge_allocation(64 + 8 * replacement_size)
                replacement = list(value)
            try:
                obj[slice(*bounds)] = replacement
            except ValueError as exc:
                raise MushyraError(f"No se puede asignar el slice: {exc}") from exc
        elif kind == "attr_assign":
            _, obj_expr, attr, value_expr = stmt
            obj = self.eval_expression(obj_expr)
            if not isinstance(obj, dict):
                raise MushyraError("Solo se pueden asignar atributos de módulos y diccionarios")
            self._set_dict_item(obj, attr, self.eval_expression(value_expr))
        elif kind == "print":
            print(self.eval_expression(stmt[1]), file=self.output)
        elif kind == "if":
            _, condition, body, elif_branches, else_body = stmt
            if ValueSemantics.truthy(self.eval_expression(condition)):
                self._eval_block(body)
                return
            for elif_condition, elif_body in elif_branches:
                if ValueSemantics.truthy(self.eval_expression(elif_condition)):
                    self._eval_block(elif_body)
                    return
            self._eval_block(else_body)
        elif kind == "match":
            subject = self.eval_expression(stmt[1])
            for pattern, guard, body in stmt[2]:
                bindings = self._match_pattern(pattern, subject)
                if bindings is None:
                    continue
                self._charge_allocation(64 + 32 * len(bindings))
                snapshot = self._install_match_bindings(bindings)
                if guard is not None:
                    try:
                        guard_matches = ValueSemantics.truthy(self.eval_expression(guard))
                    except BaseException:
                        self._restore_match_bindings(snapshot)
                        raise
                    if not guard_matches:
                        self._restore_match_bindings(snapshot)
                        continue
                self._eval_block(body)
                return
            self._eval_block(stmt[3])
        elif kind == "try":
            _, body, catches, finally_body = stmt
            try:
                try:
                    self._eval_block(body)
                except ThrownException as thrown:
                    handled = False
                    for pattern, guard, catch_body in catches:
                        bindings = self._match_pattern(pattern, thrown.value)
                        if bindings is None:
                            continue
                        self._charge_allocation(64 + 32 * len(bindings))
                        snapshot = self._install_match_bindings(bindings)
                        if guard is not None:
                            try:
                                guard_matches = ValueSemantics.truthy(self.eval_expression(guard))
                            except BaseException:
                                self._restore_match_bindings(snapshot)
                                raise
                            if not guard_matches:
                                self._restore_match_bindings(snapshot)
                                continue
                        handled = True
                        self._eval_block(catch_body)
                        break
                    if not handled:
                        raise
            finally:
                if finally_body is not None:
                    self._eval_block(finally_body)
        elif kind == "repeat":
            count = self.eval_expression(stmt[1])
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise MushyraError("repeat requiere un entero no negativo")
            for _ in range(count):
                self._tick()
                try:
                    self._eval_block(stmt[2])
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif kind == "while":
            while ValueSemantics.truthy(self.eval_expression(stmt[1])):
                self._tick()
                try:
                    self._eval_block(stmt[2])
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif kind in ("for", "each"):
            _, variable, iterable_expr, body = stmt
            iterable = self.eval_expression(iterable_expr)
            if not isinstance(iterable, (list, tuple, dict, str, range)):
                raise MushyraError("for/each requiere una lista, diccionario, string o range")
            for item in iterable:
                self._tick()
                self.set_var(variable, item)
                try:
                    self._eval_block(body)
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif kind == "func":
            _, name, params, body = stmt[:4]
            closure = self.environments[-1] if self.environments else ()
            global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
            default_values = {}
            if len(stmt) > 4:
                for parameter, expression in stmt[4]:
                    default_values[parameter] = self.eval_expression(expression)
            vararg_name = stmt[5] if len(stmt) > 5 else None
            scope = self.function_scopes.get(id(stmt)) or FunctionScope(
                frozenset(params), frozenset(), frozenset(), definition_span=getattr(stmt, "span", None)
            )
            self.set_var(name, FunctionValue(
                name, params, body, tuple(closure), global_scope,
                self.source_map, self.filename, self.current_dir,
                scope.local_names, scope.global_names, scope.nonlocal_names,
                dict(scope.free_bindings), scope.resolved_globals, scope.definition_span,
                default_values, vararg_name,
            ))
        elif kind in ("global", "nonlocal"):
            if not self.declarations:
                raise MushyraError(f"{kind} solo puede usarse dentro de una función")
            declared = self.declarations[-1][0 if kind == "global" else 1]
            other = self.declarations[-1][1 if kind == "global" else 0]
            if any(name in other for name in stmt[1]):
                raise MushyraError(f"Una variable no puede ser global y nonlocal a la vez")
            declared.update(stmt[1])
        elif kind == "return":
            raise ReturnException(self.eval_expression(stmt[1]) if stmt[1] is not None else None)
        elif kind == "throw":
            value = self._guard_value(self.eval_expression(stmt[1]))
            location = self.current_location
            contexts = (frame.format() for frame in reversed(self.call_stack))
            raise ThrownException(
                value, self.filename, location.line if location else None,
                getattr(location, "column", None) if location else None, contexts,
            )
        elif kind == "break":
            raise BreakException()
        elif kind == "continue":
            raise ContinueException()
        elif kind == "assert":
            _, condition, message = stmt
            if not ValueSemantics.truthy(self.eval_expression(condition)):
                value = self.eval_expression(message) if message is not None else "Assertion failed"
                raise MushyraError(f"Assert: {value}")
        elif kind in ("show", "say"):
            value = self.eval_expression(stmt[1])
            prefix = "👁️" if kind == "show" else "💬"
            print(f"{prefix} {value}", file=self.output)
        elif kind == "ask":
            return self.call_builtin("ask", [stmt[1]])
        elif kind == "wait":
            seconds = self.eval_expression(stmt[1])
            if (not isinstance(seconds, (int, float)) or isinstance(seconds, bool)
                    or not math.isfinite(seconds) or not 0 <= seconds <= MAX_WAIT_SECONDS):
                raise MushyraError(f"wait requiere segundos finitos entre 0 y {MAX_WAIT_SECONDS}")
            print(f"⏳ Esperando {seconds} segundos...", file=self.output)
            self.sleep(seconds)
        elif kind == "exit":
            code = self.eval_expression(stmt[1]) if stmt[1] is not None else 0
            if not isinstance(code, int) or isinstance(code, bool) or not 0 <= code <= 255:
                raise MushyraError("exit requiere un código entero entre 0 y 255")
            raise ExitException(code)
        elif kind == "pass":
            return None
        elif kind == "loop":
            while True:
                self._tick()
                try:
                    self._eval_block(stmt[1])
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif kind == "until":
            while not ValueSemantics.truthy(self.eval_expression(stmt[1])):
                self._tick()
                try:
                    self._eval_block(stmt[2])
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif kind == "unless":
            if not ValueSemantics.truthy(self.eval_expression(stmt[1])):
                self._eval_block(stmt[2])
        elif kind == "expr_stmt":
            self.eval_expression(stmt[1])
        else:
            raise MushyraError(f"Declaración interna no reconocida: {kind}")

    def _eval_block(self, statements):
        for statement in statements:
            self.eval_statement(statement)

    @staticmethod
    def _check_index(index):
        if not isinstance(index, int) or isinstance(index, bool):
            raise MushyraError("El índice debe ser un entero")

    @staticmethod
    def _eval_slice_bound(value):
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise MushyraError("Los límites y el paso de un slice deben ser enteros")
        return value

    @staticmethod
    def _comprehension_iterable(value):
        if not isinstance(value, (list, tuple, dict, str, range)):
            raise MushyraError("La comprensión requiere una lista, tupla, diccionario, string o range")
        try:
            size = len(value)
        except OverflowError as exc:
            raise MushyraError("La comprensión supera el tamaño máximo permitido") from exc
        if size > MAX_COLLECTION_ITEMS:
            raise MushyraError(f"Una comprensión no puede recorrer más de {MAX_COLLECTION_ITEMS} elementos")
        return value

    def _eval_comprehension(self, variable, item, expressions, condition):
        frame = {variable: item}
        parent_environment = self.environments[-1] if self.environments else ()
        global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
        self.environments.append((frame,) + tuple(parent_environment))
        self.declarations.append((set(), set()))
        self.global_scope_stack.append(global_scope)
        self.local_names_stack.append({variable})
        self.free_bindings_stack.append({})
        self.resolved_globals_stack.append(frozenset())
        try:
            if condition is not None and not ValueSemantics.truthy(self.eval_expression(condition)):
                return False, None
            return True, [self.eval_expression(expression) for expression in expressions]
        finally:
            self.resolved_globals_stack.pop()
            self.free_bindings_stack.pop()
            self.local_names_stack.pop()
            self.global_scope_stack.pop()
            self.declarations.pop()
            self.environments.pop()

    @classmethod
    def _collect_pattern_bindings(cls, pattern, value, bindings):
        kind = pattern[0]
        if kind == "pattern_name":
            bindings.append((pattern[1], value))
            return
        if kind == "pattern_dict":
            if not isinstance(value, dict):
                raise MushyraError("El patrón de diccionario requiere un diccionario")
            for key, child in pattern[1]:
                try:
                    item = value[key]
                except KeyError as exc:
                    raise MushyraError(f"Falta la clave {key!r} requerida por el patrón") from exc
                except TypeError as exc:
                    raise MushyraError(f"La clave {key!r} no se puede buscar en el diccionario") from exc
                cls._collect_pattern_bindings(child, item, bindings)
            return
        if kind != "pattern_list":
            raise MushyraError("Patrón de asignación no reconocido")
        if not isinstance(value, (list, tuple, str, range)):
            raise MushyraError("El patrón de lista requiere una lista, tupla, string o range")
        items = pattern[1]
        if len(value) != len(items):
            raise MushyraError(f"El patrón espera {len(items)} elementos y recibió {len(value)}")
        for child, item in zip(items, value):
            cls._collect_pattern_bindings(child, item, bindings)

    def _match_pattern(self, pattern, value):
        self._tick()
        kind = pattern[0]
        if kind == "pattern_wildcard":
            return {}
        if kind == "pattern_name":
            return {pattern[1]: value}
        if kind == "pattern_literal":
            return {} if ValueSemantics.equal(pattern[1], value, check_step=self._tick) else None
        if kind == "pattern_list":
            if not isinstance(value, (list, tuple, str, range)) or len(value) != len(pattern[1]):
                return None
            bindings = {}
            for child, item in zip(pattern[1], value):
                child_bindings = self._match_pattern(child, item)
                if child_bindings is None:
                    return None
                bindings.update(child_bindings)
            return bindings
        if kind == "pattern_dict":
            if not isinstance(value, dict):
                return None
            bindings = {}
            for key, child in pattern[1]:
                try:
                    if key not in value:
                        return None
                    item = value[key]
                except TypeError:
                    return None
                child_bindings = self._match_pattern(child, item)
                if child_bindings is None:
                    return None
                bindings.update(child_bindings)
            return bindings
        raise MushyraError(f"Patrón match interno no reconocido: {kind}")

    def _match_binding_target(self, name):
        if not self.environments:
            return self.global_scope_stack[-1] if self.global_scope_stack else self.globals
        global_names, nonlocal_names = self.declarations[-1]
        if name in global_names:
            return self.global_scope_stack[-1] if self.global_scope_stack else self.globals
        if name in nonlocal_names:
            scope_index = self.free_bindings_stack[-1].get(name)
            if scope_index is None or scope_index >= len(self.environments[-1]):
                raise MushyraError(f"nonlocal {name!r} no existe en un ámbito exterior")
            return self.environments[-1][scope_index]
        return self.environments[-1][0]

    def _install_match_bindings(self, bindings):
        snapshot = []
        try:
            for name, value in bindings.items():
                target = self._match_binding_target(name)
                existed = name in target
                previous = target.get(name)
                snapshot.append((target, name, existed, previous))
                self.set_var(name, value)
        except BaseException:
            self._restore_match_bindings(snapshot)
            raise
        return snapshot

    @staticmethod
    def _restore_match_bindings(snapshot):
        for target, name, existed, previous in reversed(snapshot):
            if existed:
                target[name] = previous
            else:
                target.pop(name, None)

    def _set_dict_item(self, mapping, key, value, charge=True):
        value = self._guard_value(value)
        try:
            is_new_key = key not in mapping
        except TypeError as exc:
            raise MushyraError("Las claves del diccionario deben ser inmutables") from exc
        if is_new_key and len(mapping) >= MAX_COLLECTION_ITEMS:
            raise MushyraError(f"Un diccionario no puede superar {MAX_COLLECTION_ITEMS} elementos")
        if is_new_key and charge:
            self._charge_allocation(64)
        mapping[key] = value

    def eval_expression(self, expr):
        if expr is None:
            return None
        self._tick()
        prior_location = self.current_location
        if isinstance(expr, ASTNode) and expr.span is not None:
            self.current_location = expr.span
        try:
            return self._guard_value(self._eval_expression(expr))
        finally:
            self.current_location = prior_location

    def _eval_expression(self, expr):
        if expr is None:
            return None
        kind = expr[0]
        try:
            if kind in ("number", "string", "bool", "null"):
                return expr[1]
            if kind == "var":
                return self.get_var(expr[1])
            if kind == "lambda":
                params, body = expr[1], expr[2]
                closure = self.environments[-1] if self.environments else ()
                global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
                self._charge_allocation(128 + 8 * len(params) + 8 * len(closure))
                return FunctionValue(
                    "<lambda>", list(params), [("return", body)], tuple(closure), global_scope,
                    self.source_map, self.filename, self.current_dir,
                    frozenset(params), definition_span=getattr(expr, "span", None),
                )
            if kind == "list":
                if len(expr[1]) > MAX_COLLECTION_ITEMS:
                    raise MushyraError(f"Una lista no puede superar {MAX_COLLECTION_ITEMS} elementos")
                result = [self.eval_expression(item) for item in expr[1]]
                self._charge_allocation(64 + 8 * len(result))
                return result
            if kind == "list_comp":
                iterable = self._comprehension_iterable(self.eval_expression(expr[3]))
                variable = expr[2][1]
                result = []
                self._charge_allocation(64)
                for item in iterable:
                    self._tick()
                    include, values = self._eval_comprehension(variable, item, (expr[1],), expr[4])
                    if include:
                        if len(result) >= MAX_COLLECTION_ITEMS:
                            raise MushyraError(f"Una lista no puede superar {MAX_COLLECTION_ITEMS} elementos")
                        self._charge_allocation(8)
                        result.append(values[0])
                return result
            if kind == "tuple":
                if len(expr[1]) > MAX_COLLECTION_ITEMS:
                    raise MushyraError(f"Una tupla no puede superar {MAX_COLLECTION_ITEMS} elementos")
                result = tuple(self.eval_expression(item) for item in expr[1])
                self._charge_allocation(48 + 8 * len(result))
                return result
            if kind == "dict":
                if len(expr[1]) > MAX_COLLECTION_ITEMS:
                    raise MushyraError(f"Un diccionario no puede superar {MAX_COLLECTION_ITEMS} elementos")
                result = {}
                for key_expr, value_expr in expr[1]:
                    key = self.eval_expression(key_expr)
                    self._set_dict_item(result, key, self.eval_expression(value_expr), charge=False)
                self._charge_allocation(128 + 64 * len(result))
                return result
            if kind == "dict_comp":
                iterable = self._comprehension_iterable(self.eval_expression(expr[4]))
                variable = expr[3][1]
                result = {}
                self._charge_allocation(128)
                for item in iterable:
                    self._tick()
                    include, values = self._eval_comprehension(
                        variable, item, (expr[1], expr[2]), expr[5]
                    )
                    if include:
                        self._set_dict_item(result, values[0], values[1])
                return result
            if kind == "index":
                obj = self.eval_expression(expr[1])
                index = self.eval_expression(expr[2])
                if isinstance(obj, dict):
                    if index not in obj:
                        raise MushyraError(f"Clave {index!r} no encontrada")
                    return obj[index]
                if isinstance(obj, (list, tuple, str, range)):
                    self._check_index(index)
                    if index < 0:
                        index += len(obj)
                    if index < 0 or index >= len(obj):
                        raise MushyraError(f"Índice {index} fuera de rango")
                    return obj[index]
                raise MushyraError("Solo se pueden indexar secuencias y diccionarios")
            if kind == "slice":
                obj = self.eval_expression(expr[1])
                if not isinstance(obj, (list, tuple, str, range)):
                    raise MushyraError(f"No se puede aplicar un slice a {self._type_name(obj)}")
                bounds = [self._eval_slice_bound(self.eval_expression(item) if item is not None else None)
                          for item in expr[2:5]]
                try:
                    result = obj[slice(*bounds)]
                except ValueError as exc:
                    raise MushyraError("El paso de un slice no puede ser cero") from exc
                if isinstance(result, (list, tuple)):
                    self._charge_allocation(64 + 8 * len(result))
                elif isinstance(result, str):
                    self._charge_allocation(49 + 4 * len(result))
                return result
            if kind == "attr":
                obj = self.eval_expression(expr[1])
                if isinstance(obj, dict) and expr[2] in obj:
                    return obj[expr[2]]
                raise MushyraError(f"Atributo {expr[2]!r} no encontrado")
            if kind == "method":
                obj = self.eval_expression(expr[1])
                args = self._eval_call_arguments(expr[3])
                if isinstance(obj, ModuleNamespace):
                    if expr[2] not in obj:
                        raise MushyraError(f"Atributo {expr[2]!r} no encontrado en el módulo")
                    return self.call_value(obj[expr[2]], args)
                if isinstance(obj, dict) and expr[2] in self.DICT_METHODS:
                    return self._call_method(obj, expr[2], args)
                if isinstance(obj, dict) and expr[2] in obj:
                    return self.call_value(obj[expr[2]], args)
                return self._call_method(obj, expr[2], args)
            if kind == "unary":
                value = self.eval_expression(expr[2])
                if expr[1] == "NOT":
                    return not ValueSemantics.truthy(value)
                if expr[1] == "MINUS":
                    if not self._is_number(value):
                        raise MushyraError("El operador - requiere un número")
                    return -value
            if kind == "binop":
                op, left_expr, right_expr = expr[1], expr[2], expr[3]
                left = self.eval_expression(left_expr)
                if op == "AND":
                    return ValueSemantics.truthy(left) and ValueSemantics.truthy(self.eval_expression(right_expr))
                if op == "OR":
                    return ValueSemantics.truthy(left) or ValueSemantics.truthy(self.eval_expression(right_expr))
                right = self.eval_expression(right_expr)
                self._guard_binary_size(op, left, right)
                if op == "PLUS":
                    if self._is_number(left) and self._is_number(right):
                        result = left + right
                    elif type(left) is type(right) and isinstance(left, (str, list, tuple)):
                        result = left + right
                    else:
                        raise MushyraError("+ requiere dos números o dos secuencias del mismo tipo")
                    if isinstance(result, (str, list, tuple)):
                        self._charge_allocation((len(result) * 4) if isinstance(result, str) else (64 + 8 * len(result)))
                    return self._guard_value(result)
                if op == "MINUS":
                    self._require_numbers(op, left, right)
                    return self._guard_value(left - right)
                if op == "MULT":
                    if self._is_number(left) and self._is_number(right):
                        result = left * right
                    elif self._is_number(left) and isinstance(right, (str, list, tuple)) and isinstance(left, int):
                        result = right * left
                    elif self._is_number(right) and isinstance(left, (str, list, tuple)) and isinstance(right, int):
                        result = left * right
                    else:
                        raise MushyraError("* requiere números o una secuencia y un entero")
                    if isinstance(result, (str, list, tuple)):
                        self._charge_allocation((len(result) * 4) if isinstance(result, str) else (64 + 8 * len(result)))
                    return self._guard_value(result)
                if op == "DIV":
                    self._require_numbers(op, left, right)
                    if right == 0:
                        raise MushyraError("División por cero")
                    return self._guard_value(left / right)
                if op == "MOD":
                    self._require_numbers(op, left, right)
                    if right == 0:
                        raise MushyraError("Módulo por cero")
                    return self._guard_value(left % right)
                if op == "EQ":
                    return ValueSemantics.equal(left, right, check_step=self._tick)
                if op == "NEQ":
                    return not ValueSemantics.equal(left, right, check_step=self._tick)
                if op == "LT":
                    return self._compare(op, left, right)
                if op == "GT":
                    return self._compare(op, left, right)
                if op == "LTE":
                    return self._compare(op, left, right)
                if op == "GTE":
                    return self._compare(op, left, right)
            if kind == "builtin":
                return self.call_builtin(expr[1], expr[2])
            if kind == "call":
                function = self.get_var(expr[1])
                args = self._eval_call_arguments(expr[2])
                return self.call_value(function, args)
        except MushyraError:
            raise
        except (TypeError, ValueError, IndexError, KeyError, ZeroDivisionError, OverflowError) as exc:
            raise self._located_error(f"Error al evaluar expresión: {exc}", exc) from exc
        raise MushyraError(f"Expresión interna no reconocida: {kind}")

    @staticmethod
    def _is_number(value):
        return ValueSemantics.is_number(value)

    def _guard_value(self, value):
        if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > MAX_INTEGER_BITS:
            raise MushyraError(f"El resultado supera el límite de {MAX_INTEGER_BITS} bits")
        if isinstance(value, float) and not math.isfinite(value):
            raise MushyraError("La operación produciría un número no finito")
        if isinstance(value, str) and len(value) > MAX_STRING_CHARACTERS:
            raise MushyraError("El resultado supera el límite de tamaño de MUSHYRA")
        if isinstance(value, (list, tuple, dict)) and len(value) > MAX_COLLECTION_ITEMS:
            raise MushyraError(f"Una colección no puede superar {MAX_COLLECTION_ITEMS} elementos")
        return value

    @staticmethod
    def _require_numbers(operator, left, right):
        if not ValueSemantics.is_number(left) or not ValueSemantics.is_number(right):
            raise MushyraError(f"{operator} requiere dos números")

    @staticmethod
    def _compare(operator, left, right):
        if not ((ValueSemantics.is_number(left) and ValueSemantics.is_number(right))
                or (isinstance(left, str) and isinstance(right, str))):
            raise MushyraError("Las comparaciones de orden requieren dos números o dos strings")
        if operator == "LT":
            return left < right
        if operator == "GT":
            return left > right
        if operator == "LTE":
            return left <= right
        return left >= right

    @staticmethod
    def _guard_binary_size(operator, left, right):
        if operator == "PLUS" and isinstance(left, (str, list, tuple)) and isinstance(right, type(left)):
            limit = MAX_STRING_CHARACTERS if isinstance(left, str) else MAX_COLLECTION_ITEMS
            if len(left) + len(right) > limit:
                raise MushyraError(f"La concatenación supera el límite de {limit} elementos")
        if operator == "MULT":
            sequence, count = (left, right) if isinstance(right, int) and not isinstance(right, bool) else (right, left)
            if isinstance(sequence, (str, list, tuple)) and isinstance(count, int) and not isinstance(count, bool):
                limit = MAX_STRING_CHARACTERS if isinstance(sequence, str) else MAX_COLLECTION_ITEMS
                if len(sequence) * max(count, 0) > limit:
                    raise MushyraError(f"La repetición supera el límite de {limit} elementos")
            if isinstance(left, int) and isinstance(right, int) and not isinstance(left, bool) and not isinstance(right, bool):
                if left and right and abs(left).bit_length() + abs(right).bit_length() > MAX_INTEGER_BITS + 1:
                    raise MushyraError(f"La multiplicación superaría el límite de {MAX_INTEGER_BITS} bits")

    def _call_method(self, obj, method, args):
        if any(isinstance(argument, NamedArgument) for argument in args):
            raise MushyraError("Los argumentos con nombre solo están disponibles para funciones MUSHYRA")
        if isinstance(obj, list):
            if method == "append":
                self._expect_arity(method, args, 1)
                if len(obj) >= MAX_COLLECTION_ITEMS:
                    raise MushyraError(f"Una lista no puede superar {MAX_COLLECTION_ITEMS} elementos")
                self._guard_value(args[0])
                self._charge_allocation(8)
                obj.append(args[0])
                return None
            if method == "pop":
                self._expect_arity(method, args, 0, 1)
                index = args[0] if args else -1
                self._check_index(index)
                if not obj:
                    raise MushyraError("pop() no puede operar sobre una lista vacía")
                if index < 0:
                    index += len(obj)
                if not 0 <= index < len(obj):
                    raise MushyraError(f"Índice {index} fuera de rango")
                return obj.pop(index)
            if method in ("clear", "reverse", "sort"):
                self._expect_arity(method, args, 0)
                try:
                    result = getattr(obj, method)()
                except TypeError as exc:
                    raise MushyraError(f"No se pueden ordenar los elementos: {exc}") from exc
                return result
        if isinstance(obj, str):
            if method in ("upper", "lower", "strip", "lstrip", "rstrip"):
                self._expect_arity(method, args, 0)
                result = getattr(obj, method)()
                self._charge_allocation(49 + 4 * len(result))
                return result
            if method == "split":
                self._expect_arity(method, args, 0, 2)
                separator = args[0] if args else None
                maxsplit = args[1] if len(args) == 2 else MAX_COLLECTION_ITEMS
                if not isinstance(maxsplit, int) or isinstance(maxsplit, bool):
                    raise MushyraError("split() requiere un límite entero de divisiones")
                if maxsplit < 0:
                    maxsplit = MAX_COLLECTION_ITEMS
                result = obj.split(separator, min(maxsplit, MAX_COLLECTION_ITEMS))
                self._guard_value(result)
                self._charge_allocation(64 + 8 * len(result) + sum(49 + 4 * len(item) for item in result))
                return result
            if method == "replace":
                self._expect_arity(method, args, 2, 3)
                old, replacement = args[:2]
                if not isinstance(old, str) or not isinstance(replacement, str):
                    raise MushyraError("replace() requiere strings para buscar y reemplazar")
                count = args[2] if len(args) == 3 else -1
                if not isinstance(count, int) or isinstance(count, bool):
                    raise MushyraError("replace() requiere un número entero de reemplazos")
                if old:
                    replacements = min(obj.count(old), count) if count >= 0 else obj.count(old)
                    predicted = len(obj) + replacements * (len(replacement) - len(old))
                else:
                    replacements = min(max(count, 0), len(obj) + 1) if count >= 0 else len(obj) + 1
                    predicted = len(obj) + replacements * len(replacement)
                if predicted > MAX_STRING_CHARACTERS:
                    raise MushyraError("replace() superaría el límite de tamaño de string")
                result = obj.replace(*args)
                self._guard_value(result)
                self._charge_allocation(49 + 4 * len(result))
                return result
        if isinstance(obj, dict):
            if method == "get":
                self._expect_arity(method, args, 1, 2)
                return obj.get(*args)
            if method == "keys":
                self._expect_arity(method, args, 0)
                self._charge_allocation(64 + 8 * len(obj))
                result = []
                for key in obj:
                    self._tick()
                    result.append(key)
                return result
            if method == "values":
                self._expect_arity(method, args, 0)
                self._charge_allocation(64 + 8 * len(obj))
                result = []
                for value in obj.values():
                    self._tick()
                    result.append(value)
                return result
            if method == "items":
                self._expect_arity(method, args, 0)
                self._charge_allocation(64 + 72 * len(obj))
                result = []
                for key, value in obj.items():
                    self._tick()
                    result.append([key, value])
                return result
            if method == "update":
                self._expect_arity(method, args, 1)
                if not isinstance(args[0], dict):
                    raise MushyraError("update() requiere un diccionario")
                additions = 0
                try:
                    for key in args[0]:
                        self._tick()
                        additions += key not in obj
                except TypeError as exc:
                    raise MushyraError("Las claves del diccionario deben ser inmutables") from exc
                if len(obj) + additions > MAX_COLLECTION_ITEMS:
                    raise MushyraError(f"Un diccionario no puede superar {MAX_COLLECTION_ITEMS} elementos")
                for value in args[0].values():
                    self._tick()
                    self._guard_value(value)
                self._charge_allocation(64 * additions)
                obj.update(args[0])
                return None
        raise MushyraError(f"Método {method!r} no disponible para {self._type_name(obj)}")

    def _eval_call_arguments(self, expressions):
        arguments = []
        for expression in expressions:
            if isinstance(expression, tuple) and expression and expression[0] == "named_arg":
                arguments.append(NamedArgument(expression[1], self.eval_expression(expression[2])))
            else:
                arguments.append(self.eval_expression(expression))
        return arguments

    @staticmethod
    def _expect_arity(name, args, minimum, maximum=None):
        maximum = minimum if maximum is None else maximum
        if not minimum <= len(args) <= maximum:
            expected = str(minimum) if minimum == maximum else f"{minimum}..{maximum}"
            raise MushyraError(f"{name}() requiere {expected} argumento(s); recibió {len(args)}")

    def call_value(self, function, args):
        from .native_stdlib import NativeFunction

        if isinstance(function, NativeFunction):
            if any(isinstance(argument, NamedArgument) for argument in args):
                raise MushyraError("Los argumentos con nombre solo están disponibles para funciones MUSHYRA")
            self._tick()
            result = self._guard_value(function.function(self, *args))
            self._tick()
            if isinstance(result, str):
                self._charge_allocation(49 + 4 * len(result))
            elif isinstance(result, (list, dict)):
                if self.budget.max_allocation_bytes is not None:
                    self._charge_allocation(
                        self._estimate_value_allocation(result, check_step=self._tick)
                    )
            return result
        if not isinstance(function, FunctionValue):
            raise MushyraError(f"{function!r} no es una función")
        positional = []
        keyword_values = {}
        for argument in args:
            if isinstance(argument, NamedArgument):
                if argument.name in keyword_values:
                    raise MushyraError(f"Argumento con nombre repetido: {argument.name!r}")
                keyword_values[argument.name] = argument.value
            else:
                positional.append(argument)
        fixed_params = (function.params[:-1] if function.vararg_name else function.params)
        if len(positional) > len(fixed_params) and function.vararg_name is None:
            raise MushyraError(f"{function.name}() acepta como máximo {len(fixed_params)} argumentos posicionales")
        unknown = sorted(set(keyword_values) - set(fixed_params))
        if unknown:
            raise MushyraError(f"{function.name}() no tiene un parámetro llamado {unknown[0]!r}")
        frame = {}
        for index, value in enumerate(positional[:len(fixed_params)]):
            parameter = fixed_params[index]
            if parameter in keyword_values:
                raise MushyraError(f"{function.name}() recibió {parameter!r} más de una vez")
            frame[parameter] = value
        frame.update(keyword_values)
        for parameter in fixed_params:
            if parameter not in frame:
                if parameter in function.default_values:
                    frame[parameter] = function.default_values[parameter]
                else:
                    raise MushyraError(f"{function.name}() requiere el argumento {parameter!r}")
        if function.vararg_name is not None:
            extra_args = positional[len(fixed_params):]
            if len(extra_args) > MAX_COLLECTION_ITEMS:
                raise MushyraError(f"{function.name}() supera el límite de elementos variádicos")
            self._charge_allocation(64 + 8 * len(extra_args))
            frame[function.vararg_name] = extra_args
        if len(self.call_stack) >= self.max_call_depth:
            raise self._located_error(f"Se superó el límite de {self.max_call_depth} llamadas anidadas")
        self._tick()
        global_names = set(function.global_names)
        nonlocal_names = set(function.nonlocal_names)
        environment = (frame,) + tuple(function.closure)
        previous_filename = self.filename
        previous_current_dir = self.current_dir
        previous_source_map = self.source_map
        call_token = self.current_location
        call_line = call_token.line if call_token else "?"
        call_column = getattr(call_token, "column", None) if call_token else None
        definition = function.definition_span
        definition_line = definition.start_line if definition else "?"
        definition_column = definition.start_column if definition else None
        if function.source_map is not None:
            self.source_map = function.source_map
        self.filename = function.filename
        self.current_dir = function.current_dir
        self.environments.append(environment)
        self.declarations.append((global_names, nonlocal_names))
        self.global_scope_stack.append(function.globals)
        self.local_names_stack.append(function.local_names)
        self.free_bindings_stack.append(function.free_bindings)
        self.resolved_globals_stack.append(function.resolved_globals)
        self.call_stack.append(CallFrame(function.name, previous_filename, call_line, call_column,
                                         function.filename, definition_line, definition_column))
        try:
            self._eval_block(function.body)
        except ReturnException as exc:
            return self._guard_value(exc.value)
        except (BreakException, ContinueException) as exc:
            signal = "break" if isinstance(exc, BreakException) else "continue"
            raise self._located_error(f"{signal} no puede salir de una función") from exc
        finally:
            self.call_stack.pop()
            self.resolved_globals_stack.pop()
            self.free_bindings_stack.pop()
            self.local_names_stack.pop()
            self.global_scope_stack.pop()
            self.declarations.pop()
            self.environments.pop()
            self.filename = previous_filename
            self.current_dir = previous_current_dir
            self.source_map = previous_source_map
        return None

    def call_builtin(self, name: str, arg_expressions: List):
        values = [self.eval_expression(arg) for arg in arg_expressions]
        if name in ("input", "ask"):
            self._expect_arity(name, values, 0, 1)
            prompt = str(values[0]) if values else ""
            if name == "ask":
                prompt = f"❓ {prompt} "
            try:
                result = self._read_input(prompt)
                if not isinstance(result, str):
                    raise MushyraError("La función de entrada debe devolver un string")
                result = self._guard_value(result)
                self._charge_allocation(49 + 4 * len(result))
                return result
            except EOFError as exc:
                raise MushyraError("No hay más entrada disponible") from exc
        if name == "len":
            self._expect_arity(name, values, 1)
            try:
                return len(values[0])
            except TypeError as exc:
                raise MushyraError("len() requiere una colección") from exc
        if name == "type":
            self._expect_arity(name, values, 1)
            return self._type_name(values[0])
        if name == "str":
            self._expect_arity(name, values, 1)
            result = self._guard_value(self._stringify(values[0]))
            self._charge_allocation(49 + 4 * len(result))
            return result
        if name == "int":
            self._expect_arity(name, values, 1)
            try:
                return int(values[0])
            except (TypeError, ValueError, OverflowError) as exc:
                raise MushyraError(f"No se puede convertir {values[0]!r} a entero") from exc
        if name == "float":
            self._expect_arity(name, values, 1)
            try:
                result = float(values[0])
                if not math.isfinite(result):
                    raise ValueError("el resultado debe ser finito")
                return result
            except (TypeError, ValueError, OverflowError) as exc:
                raise MushyraError(f"No se puede convertir {values[0]!r} a float") from exc
        if name == "range":
            self._expect_arity(name, values, 1, 3)
            if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
                raise MushyraError("range() requiere enteros")
            try:
                result = range(*values)
                if len(result) > MAX_COLLECTION_ITEMS:
                    raise MushyraError(f"range() no puede producir más de {MAX_COLLECTION_ITEMS} iteraciones")
                return result
            except ValueError as exc:
                raise MushyraError(f"range(): {exc}") from exc
            except OverflowError as exc:
                raise MushyraError("range() supera el tamaño máximo permitido") from exc
        raise MushyraError(f"Función builtin {name!r} no encontrada")

    @staticmethod
    def _type_name(value):
        if isinstance(value, FunctionValue):
            return "function"
        from .native_stdlib import NativeFunction
        if isinstance(value, NativeFunction):
            return "function"
        return ValueSemantics.type_name(value)

    @staticmethod
    def _stringify(value):
        if value is None:
            return "null"
        if value is True:
            return "true"
        if value is False:
            return "false"
        return str(value)

    def import_module(self, module: str, alias: Optional[str] = None):
        resolved_local_module = self._resolve_module(module) if self.sandbox_mode else None
        if self.sandbox_mode and resolved_local_module is None:
            self._check_native_module(module)
        if module in self.modules:
            module_scope = self.modules[module]
        else:
            module_scope = ModuleNamespace()
            self.modules[module] = module_scope  # publish before execution for cycles.
            try:
                module_path = resolved_local_module if self.sandbox_mode else self._resolve_module(module)
                if module_path is None:
                    from .native_stdlib import create_module
                    module_scope.update(create_module(module, self))
                else:
                    module_interpreter = Interpreter(
                        output=self.output,
                        input_fn=self.input,
                        max_steps=self.max_steps,
                        module_cache=self.modules,
                        budget=self.budget,
                        max_call_depth=self.max_call_depth,
                        cancel_event=self.cancel_event,
                        allowed_root=self.allowed_root,
                        call_stack=self.call_stack,
                        max_output_bytes=self.budget.max_output_bytes,
                        max_allocation_bytes=self.budget.max_allocation_bytes,
                        sandbox_mode=self.sandbox_mode,
                        debugger_hook=self.debugger_hook,
                    )
                    if module_path.stat().st_size > MAX_MODULE_SOURCE_BYTES:
                        raise MushyraError(
                            f"El módulo supera el límite de {MAX_MODULE_SOURCE_BYTES // (1024 * 1024)} MiB",
                            str(module_path),
                        )
                    with module_path.open("rb") as source_file:
                        source_bytes = source_file.read(MAX_MODULE_SOURCE_BYTES + 1)
                    if len(source_bytes) > MAX_MODULE_SOURCE_BYTES:
                        raise MushyraError(
                            f"El módulo supera el límite de {MAX_MODULE_SOURCE_BYTES // (1024 * 1024)} MiB",
                            str(module_path),
                        )
                    ast, module_interpreter.source_map = _parse_module_cached(source_bytes, module_path)
                    module_interpreter.globals = module_scope
                    module_exit_code = module_interpreter.run(ast, str(module_path))
                    if module_exit_code is not None:
                        raise ExitException(module_exit_code)
            except MushyraError as exc:
                self.modules.pop(module, None)
                exc.add_context(f"import {module}")
                raise
            except OSError as exc:
                self.modules.pop(module, None)
                raise MushyraError(f"No se pudo cargar el módulo {module!r}: {exc}", self.filename) from exc
            except Exception:
                self.modules.pop(module, None)
                raise

        if alias:
            self.set_var(alias, module_scope)
        else:
            # Preserve the original import semantics: unaliased modules expose
            # their public names in the current scope.
            for name, value in module_scope.items():
                self.set_var(name, value)

    def _resolve_module(self, module: str) -> Optional[Path]:
        parts = module.split(".")
        relative = Path(*parts)
        candidates = [
            Path(self.current_dir) / relative.with_suffix(".myr"),
            Path(self.current_dir) / relative / (parts[-1] + ".myr"),
        ]
        try:
            from .package_manager import PACKAGES_DIR
            candidates.extend([
                PACKAGES_DIR / relative.with_suffix(".myr"),
                PACKAGES_DIR / relative / (parts[-1] + ".myr"),
            ])
        except ImportError:
            pass
        for candidate in candidates:
            try:
                is_file = candidate.is_file()
                resolved = candidate.resolve() if is_file else None
            except (OSError, RuntimeError):
                continue
            if is_file:
                if self.allowed_root is not None:
                    try:
                        resolved.relative_to(self.allowed_root)
                    except ValueError:
                        continue
                return resolved
        # Modules without a user file are resolved by native_stdlib.create_module.
        return None

    def from_import_module(self, module: str, items):
        if module not in self.modules:
            self.import_module(module, alias=module.split(".")[0])
        module_scope = self.modules[module]
        for entry in items:
            if isinstance(entry, tuple):
                item, alias = entry
            else:
                item, alias = entry, None
            if item not in module_scope:
                raise MushyraError(f"{item!r} no existe en el módulo {module!r}")
            self.set_var(alias or item, module_scope[item])

    def get_var(self, name: str):
        if self.environments:
            global_names, nonlocal_names = self.declarations[-1]
            if name in global_names:
                global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
                if name in global_scope:
                    return global_scope[name]
                raise MushyraError(f"Variable global {name!r} no definida")
            if name in nonlocal_names:
                scope_index = self.free_bindings_stack[-1].get(name)
                if scope_index is not None and name in self.environments[-1][scope_index]:
                    return self.environments[-1][scope_index][name]
                raise MushyraError(f"Variable nonlocal {name!r} no definida en un ámbito exterior")
            if name in self.local_names_stack[-1]:
                if name in self.environments[-1][0]:
                    return self.environments[-1][0][name]
                raise MushyraError(f"Variable local {name!r} usada antes de asignarse")
            scope_index = self.free_bindings_stack[-1].get(name)
            if scope_index is not None:
                if name in self.environments[-1][scope_index]:
                    return self.environments[-1][scope_index][name]
                raise MushyraError(f"Variable exterior {name!r} no definida")
            if name in self.resolved_globals_stack[-1]:
                global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
                if name in global_scope:
                    return global_scope[name]
                raise MushyraError(f"Variable global {name!r} no definida")
            for scope in self.environments[-1]:
                if name in scope:
                    return scope[name]
        global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
        if name in global_scope:
            return global_scope[name]
        raise MushyraError(f"Variable {name!r} no definida")

    def set_var(self, name: str, value: Any):
        value = self._guard_value(value)
        if not self.environments:
            self.globals[name] = value
            return
        global_names, nonlocal_names = self.declarations[-1]
        if name in global_names:
            (self.global_scope_stack[-1] if self.global_scope_stack else self.globals)[name] = value
            return
        if name in nonlocal_names:
            scope_index = self.free_bindings_stack[-1].get(name)
            if scope_index is not None and scope_index < len(self.environments[-1]):
                self.environments[-1][scope_index][name] = value
                return
            raise MushyraError(f"nonlocal {name!r} no existe en un ámbito exterior")
        self.environments[-1][0][name] = value
