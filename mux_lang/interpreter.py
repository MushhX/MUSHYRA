"""Mux tree-walking interpreter."""

import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .lexer import Lexer, MuxError
from .parser import Parser


class BreakException(Exception):
    pass


class ContinueException(Exception):
    pass


class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


class ExitException(Exception):
    def __init__(self, code: int):
        self.code = code


class ModuleNamespace(dict):
    """A module's exported names, distinct from ordinary Mux dictionaries."""


@dataclass(eq=False)
class FunctionValue:
    name: str
    params: List[str]
    body: List[Any]
    closure: Tuple[Dict[str, Any], ...]
    globals: Dict[str, Any]

    def __repr__(self):
        return f"<Mux function {self.name}>"


class Interpreter:
    """Evaluate Mux ASTs with lexical function scope and embeddable IO."""

    DICT_METHODS = frozenset({"get", "keys", "values", "items", "update"})

    def __init__(self, output=None, input_fn=None, max_steps: Optional[int] = None,
                 source_map=None, module_cache=None):
        self.globals: Dict[str, Any] = {}
        self.environments: List[Tuple[Dict[str, Any], ...]] = []
        self.declarations: List[Tuple[set, set]] = []
        self.global_scope_stack: List[Dict[str, Any]] = []
        self.modules = module_cache if module_cache is not None else {}
        self.current_dir = os.getcwd()
        self.filename = "<stdin>"
        self.output = output if output is not None else sys.stdout
        self.input = input_fn if input_fn is not None else input
        if (max_steps is not None and
                (not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps < 1)):
            raise ValueError("max_steps debe ser un entero positivo o None")
        self.max_steps = max_steps
        self.steps = 0
        self.source_map = source_map or {}
        self.current_location = None
        self.call_stack = []

    def run(self, ast: List[Any], filename: str = "<stdin>"):
        self.filename = filename
        self.current_dir = os.path.dirname(os.path.abspath(filename)) if filename != "<stdin>" else os.getcwd()
        self.steps = 0
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
        return None

    def _located_error(self, message, cause=None):
        token = self.current_location
        return MuxError(
            message,
            path=self.filename,
            line=token.line if token else None,
            column=token.column if token else None,
            cause=cause,
        )

    def _tick(self):
        self.steps += 1
        if self.max_steps is not None and self.steps > self.max_steps:
            raise self._located_error(f"Se alcanzó el límite de {self.max_steps} pasos de ejecución")

    def eval_statement(self, stmt):
        if not stmt:
            return None
        prior_location = self.current_location
        self.current_location = self.source_map.get(id(stmt), prior_location)
        try:
            self._tick()
            return self._eval_statement(stmt)
        except MuxError as exc:
            token = self.source_map.get(id(stmt))
            if token:
                exc.set_location(self.filename, token.line, token.column)
            if exc.cause is None and exc.__cause__ is not None:
                exc.cause = exc.__cause__
            if self.call_stack:
                name, path, line = self.call_stack[-1]
                exc.add_context(f"función {name} ({path}:{line})")
            raise
        except (TypeError, ValueError, IndexError, KeyError, ZeroDivisionError, OverflowError) as exc:
            error = self._located_error(f"Error de ejecución: {exc}", exc)
            if self.call_stack:
                name, path, line = self.call_stack[-1]
                error.add_context(f"función {name} ({path}:{line})")
            raise error from exc
        except (BreakException, ContinueException, ReturnException, ExitException):
            raise
        except Exception as exc:
            error = self._located_error(f"Error de ejecución: {exc}", exc)
            if self.call_stack:
                name, path, line = self.call_stack[-1]
                error.add_context(f"función {name} ({path}:{line})")
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
                    raise MuxError(f"Índice {index} fuera de rango")
                obj[index] = value
            elif isinstance(obj, dict):
                obj[index] = value
            else:
                raise MuxError("Solo se puede asignar un índice de lista o diccionario")
        elif kind == "attr_assign":
            _, obj_expr, attr, value_expr = stmt
            obj = self.eval_expression(obj_expr)
            if not isinstance(obj, dict):
                raise MuxError("Solo se pueden asignar atributos de módulos y diccionarios")
            obj[attr] = self.eval_expression(value_expr)
        elif kind == "print":
            print(self.eval_expression(stmt[1]), file=self.output)
        elif kind == "if":
            _, condition, body, elif_branches, else_body = stmt
            if self.eval_expression(condition):
                self._eval_block(body)
                return
            for elif_condition, elif_body in elif_branches:
                if self.eval_expression(elif_condition):
                    self._eval_block(elif_body)
                    return
            self._eval_block(else_body)
        elif kind == "repeat":
            count = self.eval_expression(stmt[1])
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise MuxError("repeat requiere un entero no negativo")
            for _ in range(count):
                self._tick()
                try:
                    self._eval_block(stmt[2])
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif kind == "while":
            while self.eval_expression(stmt[1]):
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
                raise MuxError("for/each requiere una lista, diccionario, string o range")
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
            _, name, params, body = stmt
            closure = self.environments[-1] if self.environments else ()
            global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
            self.set_var(name, FunctionValue(name, params, body, tuple(closure), global_scope))
        elif kind in ("global", "nonlocal"):
            if not self.declarations:
                raise MuxError(f"{kind} solo puede usarse dentro de una función")
            declared = self.declarations[-1][0 if kind == "global" else 1]
            other = self.declarations[-1][1 if kind == "global" else 0]
            if any(name in other for name in stmt[1]):
                raise MuxError(f"Una variable no puede ser global y nonlocal a la vez")
            declared.update(stmt[1])
        elif kind == "return":
            raise ReturnException(self.eval_expression(stmt[1]) if stmt[1] is not None else None)
        elif kind == "break":
            raise BreakException()
        elif kind == "continue":
            raise ContinueException()
        elif kind == "assert":
            _, condition, message = stmt
            if not self.eval_expression(condition):
                value = self.eval_expression(message) if message is not None else "Assertion failed"
                raise MuxError(f"Assert: {value}")
        elif kind in ("show", "say"):
            value = self.eval_expression(stmt[1])
            prefix = "👁️" if kind == "show" else "💬"
            print(f"{prefix} {value}", file=self.output)
        elif kind == "ask":
            return self.call_builtin("ask", [stmt[1]])
        elif kind == "wait":
            seconds = self.eval_expression(stmt[1])
            if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not math.isfinite(seconds) or seconds < 0:
                raise MuxError("wait requiere segundos finitos y no negativos")
            print(f"⏳ Esperando {seconds} segundos...", file=self.output)
            time.sleep(seconds)
        elif kind == "exit":
            code = self.eval_expression(stmt[1]) if stmt[1] is not None else 0
            if not isinstance(code, int) or isinstance(code, bool) or not 0 <= code <= 255:
                raise MuxError("exit requiere un código entero entre 0 y 255")
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
            while not self.eval_expression(stmt[1]):
                self._tick()
                try:
                    self._eval_block(stmt[2])
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif kind == "unless":
            if not self.eval_expression(stmt[1]):
                self._eval_block(stmt[2])
        elif kind == "expr_stmt":
            self.eval_expression(stmt[1])
        else:
            raise MuxError(f"Declaración interna no reconocida: {kind}")

    def _eval_block(self, statements):
        for statement in statements:
            self.eval_statement(statement)

    @staticmethod
    def _check_index(index):
        if not isinstance(index, int) or isinstance(index, bool):
            raise MuxError("El índice debe ser un entero")

    def eval_expression(self, expr):
        if expr is None:
            return None
        kind = expr[0]
        try:
            if kind in ("number", "string", "bool", "null"):
                return expr[1]
            if kind == "var":
                return self.get_var(expr[1])
            if kind == "list":
                return [self.eval_expression(item) for item in expr[1]]
            if kind == "dict":
                result = {}
                for key_expr, value_expr in expr[1]:
                    key = self.eval_expression(key_expr)
                    try:
                        result[key] = self.eval_expression(value_expr)
                    except TypeError as exc:
                        raise MuxError("Las claves del diccionario deben ser inmutables") from exc
                return result
            if kind == "index":
                obj = self.eval_expression(expr[1])
                index = self.eval_expression(expr[2])
                if isinstance(obj, dict):
                    if index not in obj:
                        raise MuxError(f"Clave {index!r} no encontrada")
                    return obj[index]
                if isinstance(obj, (list, tuple, str)):
                    self._check_index(index)
                    if index < 0:
                        index += len(obj)
                    if index < 0 or index >= len(obj):
                        raise MuxError(f"Índice {index} fuera de rango")
                    return obj[index]
                raise MuxError("Solo se puede indexar listas, strings y diccionarios")
            if kind == "attr":
                obj = self.eval_expression(expr[1])
                if isinstance(obj, dict) and expr[2] in obj:
                    return obj[expr[2]]
                raise MuxError(f"Atributo {expr[2]!r} no encontrado")
            if kind == "method":
                obj = self.eval_expression(expr[1])
                args = [self.eval_expression(arg) for arg in expr[3]]
                if isinstance(obj, ModuleNamespace):
                    if expr[2] not in obj:
                        raise MuxError(f"Atributo {expr[2]!r} no encontrado en el módulo")
                    return self.call_value(obj[expr[2]], args)
                if isinstance(obj, dict) and expr[2] in self.DICT_METHODS:
                    return self._call_method(obj, expr[2], args)
                if isinstance(obj, dict) and expr[2] in obj:
                    return self.call_value(obj[expr[2]], args)
                return self._call_method(obj, expr[2], args)
            if kind == "unary":
                value = self.eval_expression(expr[2])
                if expr[1] == "NOT":
                    return not bool(value)
                if expr[1] == "MINUS":
                    if not self._is_number(value):
                        raise MuxError("El operador - requiere un número")
                    return -value
            if kind == "binop":
                op, left_expr, right_expr = expr[1], expr[2], expr[3]
                left = self.eval_expression(left_expr)
                if op == "AND":
                    return bool(left) and bool(self.eval_expression(right_expr))
                if op == "OR":
                    return bool(left) or bool(self.eval_expression(right_expr))
                right = self.eval_expression(right_expr)
                if op == "PLUS":
                    return left + right
                if op == "MINUS":
                    return left - right
                if op == "MULT":
                    return left * right
                if op == "DIV":
                    if right == 0:
                        raise MuxError("División por cero")
                    return left / right
                if op == "MOD":
                    if right == 0:
                        raise MuxError("Módulo por cero")
                    return left % right
                if op == "EQ":
                    return self._strict_equal(left, right)
                if op == "NEQ":
                    return not self._strict_equal(left, right)
                if op == "LT":
                    return left < right
                if op == "GT":
                    return left > right
                if op == "LTE":
                    return left <= right
                if op == "GTE":
                    return left >= right
            if kind == "builtin":
                return self.call_builtin(expr[1], expr[2])
            if kind == "call":
                function = self.get_var(expr[1])
                args = [self.eval_expression(arg) for arg in expr[2]]
                return self.call_value(function, args)
        except MuxError:
            raise
        except (TypeError, ValueError, IndexError, KeyError, ZeroDivisionError, OverflowError) as exc:
            raise self._located_error(f"Error al evaluar expresión: {exc}", exc) from exc
        raise MuxError(f"Expresión interna no reconocida: {kind}")

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def _strict_equal(cls, left, right):
        if cls._is_number(left) and cls._is_number(right):
            return left == right
        if type(left) is not type(right):
            return False
        return left == right

    def _call_method(self, obj, method, args):
        if isinstance(obj, list):
            if method == "append":
                self._expect_arity(method, args, 1)
                obj.append(args[0])
                return None
            if method == "pop":
                self._expect_arity(method, args, 0, 1)
                index = args[0] if args else -1
                self._check_index(index)
                if not obj:
                    raise MuxError("pop() no puede operar sobre una lista vacía")
                if index < 0:
                    index += len(obj)
                if not 0 <= index < len(obj):
                    raise MuxError(f"Índice {index} fuera de rango")
                return obj.pop(index)
            if method in ("clear", "reverse", "sort"):
                self._expect_arity(method, args, 0)
                try:
                    result = getattr(obj, method)()
                except TypeError as exc:
                    raise MuxError(f"No se pueden ordenar los elementos: {exc}") from exc
                return result
        if isinstance(obj, str):
            if method in ("upper", "lower", "strip", "lstrip", "rstrip"):
                self._expect_arity(method, args, 0)
                return getattr(obj, method)()
            if method == "split":
                self._expect_arity(method, args, 0, 2)
                return obj.split(*args)
            if method == "replace":
                self._expect_arity(method, args, 2, 3)
                return obj.replace(*args)
        if isinstance(obj, dict):
            if method == "get":
                self._expect_arity(method, args, 1, 2)
                return obj.get(*args)
            if method == "keys":
                self._expect_arity(method, args, 0)
                return list(obj.keys())
            if method == "values":
                self._expect_arity(method, args, 0)
                return list(obj.values())
            if method == "items":
                self._expect_arity(method, args, 0)
                return [list(item) for item in obj.items()]
            if method == "update":
                self._expect_arity(method, args, 1)
                if not isinstance(args[0], dict):
                    raise MuxError("update() requiere un diccionario")
                obj.update(args[0])
                return None
        raise MuxError(f"Método {method!r} no disponible para {self._type_name(obj)}")

    @staticmethod
    def _expect_arity(name, args, minimum, maximum=None):
        maximum = minimum if maximum is None else maximum
        if not minimum <= len(args) <= maximum:
            expected = str(minimum) if minimum == maximum else f"{minimum}..{maximum}"
            raise MuxError(f"{name}() requiere {expected} argumento(s); recibió {len(args)}")

    @staticmethod
    def _function_declarations(statements):
        global_names, nonlocal_names = set(), set()

        def collect(block):
            for statement in block:
                kind = statement[0]
                if kind == "global":
                    global_names.update(statement[1])
                elif kind == "nonlocal":
                    nonlocal_names.update(statement[1])
                elif kind == "if":
                    collect(statement[2])
                    for _, branch in statement[3]:
                        collect(branch)
                    collect(statement[4])
                elif kind in ("repeat", "while", "loop", "until", "unless"):
                    collect(statement[-1])
                elif kind in ("for", "each"):
                    collect(statement[3])

        collect(statements)
        return global_names, nonlocal_names

    def call_value(self, function, args):
        from .native_stdlib import NativeFunction

        if isinstance(function, NativeFunction):
            return function.function(self, *args)
        if not isinstance(function, FunctionValue):
            raise MuxError(f"{function!r} no es una función")
        self._expect_arity(function.name, args, len(function.params))
        global_names, nonlocal_names = self._function_declarations(function.body)
        if global_names.intersection(nonlocal_names):
            raise MuxError("Una variable no puede ser global y nonlocal a la vez")
        declared_names = global_names.union(nonlocal_names)
        if declared_names.intersection(function.params):
            raise MuxError("Un parámetro no puede declararse global o nonlocal")
        frame = dict(zip(function.params, args))
        environment = (frame,) + tuple(function.closure)
        self.environments.append(environment)
        self.declarations.append((global_names, nonlocal_names))
        self.global_scope_stack.append(function.globals)
        call_token = self.current_location
        self.call_stack.append((function.name, self.filename, call_token.line if call_token else "?"))
        try:
            self._eval_block(function.body)
        except ReturnException as exc:
            return exc.value
        except (BreakException, ContinueException) as exc:
            signal = "break" if isinstance(exc, BreakException) else "continue"
            raise self._located_error(f"{signal} no puede salir de una función") from exc
        finally:
            self.call_stack.pop()
            self.global_scope_stack.pop()
            self.declarations.pop()
            self.environments.pop()
        return None

    def call_builtin(self, name: str, arg_expressions: List):
        values = [self.eval_expression(arg) for arg in arg_expressions]
        if name in ("input", "ask"):
            self._expect_arity(name, values, 0, 1)
            prompt = str(values[0]) if values else ""
            if name == "ask":
                prompt = f"❓ {prompt} "
            try:
                return self.input(prompt)
            except EOFError as exc:
                raise MuxError("No hay más entrada disponible") from exc
        if name == "len":
            self._expect_arity(name, values, 1)
            try:
                return len(values[0])
            except TypeError as exc:
                raise MuxError("len() requiere una colección") from exc
        if name == "type":
            self._expect_arity(name, values, 1)
            return self._type_name(values[0])
        if name == "str":
            self._expect_arity(name, values, 1)
            return self._stringify(values[0])
        if name == "int":
            self._expect_arity(name, values, 1)
            try:
                return int(values[0])
            except (TypeError, ValueError, OverflowError) as exc:
                raise MuxError(f"No se puede convertir {values[0]!r} a entero") from exc
        if name == "float":
            self._expect_arity(name, values, 1)
            try:
                result = float(values[0])
                if not math.isfinite(result):
                    raise ValueError("el resultado debe ser finito")
                return result
            except (TypeError, ValueError, OverflowError) as exc:
                raise MuxError(f"No se puede convertir {values[0]!r} a float") from exc
        if name == "range":
            self._expect_arity(name, values, 1, 3)
            if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
                raise MuxError("range() requiere enteros")
            try:
                return range(*values)
            except ValueError as exc:
                raise MuxError(f"range(): {exc}") from exc
        raise MuxError(f"Función builtin {name!r} no encontrada")

    @staticmethod
    def _type_name(value):
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "list"
        if isinstance(value, dict):
            return "dictionary"
        if isinstance(value, range):
            return "range"
        if isinstance(value, FunctionValue):
            return "function"
        from .native_stdlib import NativeFunction
        if isinstance(value, NativeFunction):
            return "function"
        return type(value).__name__

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
        if module in self.modules:
            module_scope = self.modules[module]
        else:
            module_scope = ModuleNamespace()
            self.modules[module] = module_scope  # publish before execution for cycles.
            try:
                module_path = self._resolve_module(module)
                if module_path is None:
                    from .native_stdlib import create_module
                    module_scope.update(create_module(module, self))
                else:
                    module_interpreter = Interpreter(
                        output=self.output,
                        input_fn=self.input,
                        max_steps=self.max_steps,
                        module_cache=self.modules,
                    )
                    code = module_path.read_text(encoding="utf-8")
                    lexer = Lexer(code, str(module_path))
                    tokens = lexer.tokenize()
                    parser = Parser(tokens, str(module_path))
                    module_interpreter.source_map = parser.source_map
                    ast = parser.parse()
                    module_interpreter.globals = module_scope
                    module_exit_code = module_interpreter.run(ast, str(module_path))
                    if module_exit_code is not None:
                        raise ExitException(module_exit_code)
            except MuxError as exc:
                self.modules.pop(module, None)
                exc.add_context(f"import {module}")
                raise
            except OSError as exc:
                self.modules.pop(module, None)
                raise MuxError(f"No se pudo cargar el módulo {module!r}: {exc}", self.filename) from exc
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
            Path(self.current_dir) / relative.with_suffix(".mux"),
            Path(self.current_dir) / relative / (parts[-1] + ".mux"),
        ]
        try:
            from .package_manager import PACKAGES_DIR
            candidates.extend([
                PACKAGES_DIR / relative.with_suffix(".mux"),
                PACKAGES_DIR / relative / (parts[-1] + ".mux"),
            ])
        except ImportError:
            pass
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
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
                raise MuxError(f"{item!r} no existe en el módulo {module!r}")
            self.set_var(alias or item, module_scope[item])

    def get_var(self, name: str):
        if self.environments:
            global_names, nonlocal_names = self.declarations[-1]
            if name in global_names:
                global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
                if name in global_scope:
                    return global_scope[name]
                raise MuxError(f"Variable global {name!r} no definida")
            if name in nonlocal_names:
                for scope in self.environments[-1][1:]:
                    if name in scope:
                        return scope[name]
                raise MuxError(f"Variable nonlocal {name!r} no definida en un ámbito exterior")
            for scope in self.environments[-1]:
                if name in scope:
                    return scope[name]
        global_scope = self.global_scope_stack[-1] if self.global_scope_stack else self.globals
        if name in global_scope:
            return global_scope[name]
        raise MuxError(f"Variable {name!r} no definida")

    def set_var(self, name: str, value: Any):
        if not self.environments:
            self.globals[name] = value
            return
        global_names, nonlocal_names = self.declarations[-1]
        if name in global_names:
            (self.global_scope_stack[-1] if self.global_scope_stack else self.globals)[name] = value
            return
        if name in nonlocal_names:
            for scope in self.environments[-1][1:]:
                if name in scope:
                    scope[name] = value
                    return
            raise MuxError(f"nonlocal {name!r} no existe en un ámbito exterior")
        self.environments[-1][0][name] = value
