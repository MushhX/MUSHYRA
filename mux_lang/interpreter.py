"""
Mux Interpreter - Intérprete Principal
Creador: MushhX
"""

import sys
import os
from typing import Any, Dict, List, Optional
from .lexer import MuxError

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class Interpreter:
    """Intérprete de Mux"""
    
    def __init__(self):
        self.globals = {}
        self.locals_stack = []
        self.modules = {}
        self.current_dir = os.getcwd()
        
    def run(self, ast: List[Any], filename: str = '<stdin>'):
        self.current_dir = os.path.dirname(os.path.abspath(filename)) if filename != '<stdin>' else os.getcwd()
        
        try:
            for statement in ast:
                result = self.eval_statement(statement)
                if isinstance(result, ReturnException):
                    return result.value
        except MuxError as e:
            print(f"\n{e}")
            sys.exit(1)
        except (BreakException, ContinueException) as e:
            print(f"\n❌ {e.__class__.__name__} fuera de un bucle")
            sys.exit(1)
    
    def eval_statement(self, stmt):
        if not stmt:
            return None
            
        stmt_type = stmt[0]
        
        if stmt_type == 'import':
            _, module, alias = stmt
            self.import_module(module, alias)
        
        elif stmt_type == 'from_import':
            _, module, items = stmt
            self.from_import_module(module, items)
        
        elif stmt_type == 'let':
            _, name, value = stmt
            val = self.eval_expression(value)
            self.set_var(name, val)
        
        elif stmt_type == 'assign':
            _, name, value = stmt
            val = self.eval_expression(value)
            self.set_var(name, val)
        
        elif stmt_type == 'index_assign':
            _, name, index_expr, value = stmt
            obj = self.get_var(name)
            index = self.eval_expression(index_expr)
            val = self.eval_expression(value)
            
            if isinstance(obj, list):
                if not isinstance(index, int):
                    raise MuxError("❌ El índice debe ser un número entero")
                if index < 0 or index >= len(obj):
                    raise MuxError(f"❌ Índice {index} fuera de rango")
                obj[index] = val
            elif isinstance(obj, dict):
                obj[index] = val
            else:
                raise MuxError("❌ Solo se puede indexar listas y diccionarios")
        
        elif stmt_type == 'print':
            _, expr = stmt
            val = self.eval_expression(expr)
            print(val)
        
        elif stmt_type == 'if':
            _, condition, body, elif_branches, else_body = stmt
            if self.eval_expression(condition):
                for s in body:
                    self.eval_statement(s)
            else:
                executed = False
                for elif_cond, elif_body in elif_branches:
                    if self.eval_expression(elif_cond):
                        for s in elif_body:
                            self.eval_statement(s)
                        executed = True
                        break
                if not executed:
                    for s in else_body:
                        self.eval_statement(s)
        
        elif stmt_type == 'repeat':
            _, times_expr, body = stmt
            times = self.eval_expression(times_expr)
            if not isinstance(times, int):
                raise MuxError("❌ repeat requiere un número entero")
            for _ in range(times):
                try:
                    for s in body:
                        self.eval_statement(s)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif stmt_type == 'while':
            _, condition, body = stmt
            while self.eval_expression(condition):
                try:
                    for s in body:
                        self.eval_statement(s)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif stmt_type == 'for':
            _, var, iterable_expr, body = stmt
            iterable = self.eval_expression(iterable_expr)
            
            if not hasattr(iterable, '__iter__'):
                raise MuxError("❌ for requiere un iterable (lista, rango, etc.)")
            
            for item in iterable:
                self.set_var(var, item)
                try:
                    for s in body:
                        self.eval_statement(s)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif stmt_type == 'func':
            _, name, params, body = stmt
            self.set_var(name, ('function', params, body))
        
        elif stmt_type == 'return':
            _, value = stmt
            raise ReturnException(self.eval_expression(value) if value else None)
        
        elif stmt_type == 'break':
            raise BreakException()
        
        elif stmt_type == 'continue':
            raise ContinueException()
        
        elif stmt_type == 'assert':
            _, condition, message = stmt
            if not self.eval_expression(condition):
                msg = self.eval_expression(message) if message else "Assertion failed"
                raise MuxError(f"❌ Assert: {msg}")
        
        elif stmt_type == 'show':
            _, expr = stmt
            val = self.eval_expression(expr)
            print(f"👁️ {val}")
        
        elif stmt_type == 'ask':
            _, prompt = stmt
            prompt_text = self.eval_expression(prompt)
            return input(f"❓ {prompt_text} ")
        
        elif stmt_type == 'say':
            _, message = stmt
            msg = self.eval_expression(message)
            print(f"💬 {msg}")
        
        elif stmt_type == 'wait':
            _, seconds = stmt
            secs = self.eval_expression(seconds)
            print(f"⏳ Esperando {secs} segundos...")
            import time
            time.sleep(secs)
        
        elif stmt_type == 'exit':
            _, code = stmt
            exit_code = self.eval_expression(code) if code else 0
            print(f"👋 Saliendo con código {exit_code}")
            sys.exit(exit_code)
        
        elif stmt_type == 'pass':
            pass
        
        elif stmt_type == 'loop':
            _, body = stmt
            while True:
                try:
                    for s in body:
                        self.eval_statement(s)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif stmt_type == 'until':
            _, condition, body = stmt
            while not self.eval_expression(condition):
                try:
                    for s in body:
                        self.eval_statement(s)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif stmt_type == 'unless':
            _, condition, body = stmt
            if not self.eval_expression(condition):
                for s in body:
                    self.eval_statement(s)
        
        elif stmt_type == 'each':
            _, var, iterable_expr, body = stmt
            iterable = self.eval_expression(iterable_expr)
            if not hasattr(iterable, '__iter__'):
                raise MuxError("❌ each requiere un iterable")
            for item in iterable:
                self.set_var(var, item)
                try:
                    for s in body:
                        self.eval_statement(s)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif stmt_type == 'call':
            self.eval_expression(stmt)
        
        elif stmt_type == 'method_call':
            self.eval_expression(stmt)
        
        elif stmt_type == 'expr_stmt':
            _, expr = stmt
            self.eval_expression(expr)
        
        return None

    def eval_expression(self, expr):
        if not expr:
            return None
            
        expr_type = expr[0]
        
        if expr_type == 'number':
            return expr[1]
        elif expr_type == 'string':
            return expr[1]
        elif expr_type == 'bool':
            return expr[1]
        elif expr_type == 'var':
            return self.get_var(expr[1])
        
        elif expr_type == 'list':
            _, elements = expr
            return [self.eval_expression(e) for e in elements]
        
        elif expr_type == 'dict':
            _, pairs = expr
            result = {}
            for key_expr, val_expr in pairs:
                key = self.eval_expression(key_expr)
                val = self.eval_expression(val_expr)
                result[key] = val
            return result
        
        elif expr_type == 'index':
            _, obj_expr, index_expr = expr
            obj = self.eval_expression(obj_expr)
            index = self.eval_expression(index_expr)
            
            if isinstance(obj, (list, str)):
                if not isinstance(index, int):
                    raise MuxError("❌ El índice debe ser un número entero")
                if index < 0 or index >= len(obj):
                    raise MuxError(f"❌ Índice {index} fuera de rango")
                return obj[index]
            elif isinstance(obj, dict):
                if index not in obj:
                    raise MuxError(f"❌ Clave '{index}' no encontrada")
                return obj[index]
            else:
                raise MuxError("❌ Solo se puede indexar listas, strings y diccionarios")
        
        elif expr_type == 'attr':
            _, obj_expr, attr = expr
            obj = self.eval_expression(obj_expr)
            if isinstance(obj, dict) and attr in obj:
                return obj[attr]
            raise MuxError(f"❌ Atributo '{attr}' no encontrado")
        
        elif expr_type == 'method':
            _, obj_expr, method, args = expr
            obj = self.eval_expression(obj_expr)
            arg_vals = [self.eval_expression(arg) for arg in args]
            
            # Métodos de lista
            if isinstance(obj, list):
                if method == 'append':
                    if len(arg_vals) != 1:
                        raise MuxError("❌ append() requiere 1 argumento")
                    obj.append(arg_vals[0])
                    return None
                elif method == 'pop':
                    if len(arg_vals) > 1:
                        raise MuxError("❌ pop() requiere 0 o 1 argumento")
                    index = arg_vals[0] if arg_vals else -1
                    return obj.pop(index)
                elif method == 'clear':
                    obj.clear()
                    return None
                elif method == 'reverse':
                    obj.reverse()
                    return None
                elif method == 'sort':
                    obj.sort()
                    return None
            
            # Métodos de string
            elif isinstance(obj, str):
                if method == 'upper':
                    return obj.upper()
                elif method == 'lower':
                    return obj.lower()
                elif method == 'split':
                    sep = arg_vals[0] if arg_vals else None
                    return obj.split(sep)
                elif method == 'replace':
                    if len(arg_vals) != 2:
                        raise MuxError("❌ replace() requiere 2 argumentos")
                    return obj.replace(arg_vals[0], arg_vals[1])
                elif method == 'strip':
                    return obj.strip()
            
            raise MuxError(f"❌ Método '{method}' no encontrado")
        
        elif expr_type == 'unary':
            _, op, operand = expr
            val = self.eval_expression(operand)
            if op == 'NOT':
                return not val
            elif op == 'MINUS':
                return -val
        
        elif expr_type == 'binop':
            _, op, left, right = expr
            left_val = self.eval_expression(left)
            right_val = self.eval_expression(right)
            
            if op == 'PLUS':
                return left_val + right_val
            elif op == 'MINUS':
                return left_val - right_val
            elif op == 'MULT':
                return left_val * right_val
            elif op == 'DIV':
                if right_val == 0:
                    raise MuxError("❌ División por cero")
                return left_val / right_val
            elif op == 'MOD':
                return left_val % right_val
            elif op == 'EQ':
                return left_val == right_val
            elif op == 'NEQ':
                return left_val != right_val
            elif op == 'LT':
                return left_val < right_val
            elif op == 'GT':
                return left_val > right_val
            elif op == 'LTE':
                return left_val <= right_val
            elif op == 'GTE':
                return left_val >= right_val
            elif op == 'AND':
                return left_val and right_val
            elif op == 'OR':
                return left_val or right_val
        
        elif expr_type == 'builtin':
            _, name, args = expr
            return self.call_builtin(name, args)
        
        elif expr_type == 'call':
            _, name, args = expr
            func = self.get_var(name)
            
            if not isinstance(func, tuple) or func[0] != 'function':
                raise MuxError(f"❌ '{name}' no es una función")
            
            _, params, body = func
            if len(args) != len(params):
                raise MuxError(f"❌ '{name}' espera {len(params)} argumentos, recibió {len(args)}")
            
            local_scope = {}
            for param, arg in zip(params, args):
                local_scope[param] = self.eval_expression(arg)
            
            self.locals_stack.append(local_scope)
            result = None
            try:
                for stmt in body:
                    self.eval_statement(stmt)
            except ReturnException as e:
                result = e.value
            finally:
                self.locals_stack.pop()
            
            return result
        
        elif expr_type == 'method_call':
            _, obj_name, method, args = expr
            obj = self.get_var(obj_name)
            arg_vals = [self.eval_expression(arg) for arg in args]
            
            if isinstance(obj, list):
                if method == 'append':
                    if len(arg_vals) != 1:
                        raise MuxError("❌ append() requiere 1 argumento")
                    obj.append(arg_vals[0])
                    return None
            
            raise MuxError(f"❌ Método '{method}' no encontrado")
        
        return None
    
    def call_builtin(self, name: str, args: List):
        arg_vals = [self.eval_expression(arg) for arg in args]
        
        if name == 'input':
            prompt = arg_vals[0] if arg_vals else ""
            return input(prompt)
        elif name == 'len':
            if len(arg_vals) != 1:
                raise MuxError("❌ len() requiere 1 argumento")
            return len(arg_vals[0])
        elif name == 'type':
            if len(arg_vals) != 1:
                raise MuxError("❌ type() requiere 1 argumento")
            return type(arg_vals[0]).__name__
        elif name == 'str':
            if len(arg_vals) != 1:
                raise MuxError("❌ str() requiere 1 argumento")
            return str(arg_vals[0])
        elif name == 'int':
            if len(arg_vals) != 1:
                raise MuxError("❌ int() requiere 1 argumento")
            try:
                return int(arg_vals[0])
            except ValueError:
                raise MuxError(f"❌ No se puede convertir '{arg_vals[0]}' a entero")
        elif name == 'float':
            if len(arg_vals) != 1:
                raise MuxError("❌ float() requiere 1 argumento")
            try:
                return float(arg_vals[0])
            except ValueError:
                raise MuxError(f"❌ No se puede convertir '{arg_vals[0]}' a float")
        elif name == 'range':
            if len(arg_vals) == 1:
                return range(arg_vals[0])
            elif len(arg_vals) == 2:
                return range(arg_vals[0], arg_vals[1])
            elif len(arg_vals) == 3:
                return range(arg_vals[0], arg_vals[1], arg_vals[2])
            else:
                raise MuxError("❌ range() requiere 1, 2 o 3 argumentos")
        
        raise MuxError(f"❌ Función builtin '{name}' no encontrada")
    
    def import_module(self, module: str, alias: Optional[str] = None):
        if module in self.modules:
            module_scope = self.modules[module]
            if alias:
                self.set_var(alias, module_scope)
            else:
                # Importar todas las variables del módulo al scope global
                for name, value in module_scope.items():
                    self.set_var(name, value)
            return
        
        # Buscar archivo .mux
        module_path = os.path.join(self.current_dir, f"{module}.mux")
        if not os.path.exists(module_path):
            # Buscar en stdlib
            stdlib_path = os.path.join(os.path.dirname(__file__), 'stdlib', f"{module}.mux")
            if os.path.exists(stdlib_path):
                module_path = stdlib_path
            else:
                raise MuxError(f"❌ Módulo '{module}' no encontrado")
        
        # Cargar y ejecutar módulo
        from .lexer import Lexer
        from .parser import Parser
        
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Crear scope para el módulo
        module_interpreter = Interpreter()
        module_interpreter.run(ast, module_path)
        
        self.modules[module] = module_interpreter.globals
        
        if alias:
            self.set_var(alias, module_interpreter.globals)
        else:
            # Importar todas las variables del módulo al scope global
            for name, value in module_interpreter.globals.items():
                self.set_var(name, value)
    
    def from_import_module(self, module: str, items: List[str]):
        if module not in self.modules:
            self.import_module(module)
        
        module_scope = self.modules[module]
        for item in items:
            if item not in module_scope:
                raise MuxError(f"❌ '{item}' no encontrado en módulo '{module}'")
            self.set_var(item, module_scope[item])
    
    def get_var(self, name: str):
        for scope in reversed(self.locals_stack):
            if name in scope:
                return scope[name]
        if name in self.globals:
            return self.globals[name]
        raise MuxError(f"❌ Variable '{name}' no definida")
    
    def set_var(self, name: str, value: Any):
        if self.locals_stack:
            self.locals_stack[-1][name] = value
        else:
            self.globals[name] = value
