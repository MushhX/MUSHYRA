#!/usr/bin/env python3
"""
Mux Programming Language Interpreter
Un lenguaje moderno, accesible y ligero
"""

import sys
import re
from typing import Any, Dict, List, Optional

class MuxError(Exception):
    """Error base de Mux con mensajes comprensibles"""
    pass

class Lexer:
    """Analizador léxico para Mux"""
    
    TOKEN_PATTERNS = [
        ('NUMBER', r'\d+(\.\d+)?'),
        ('STRING', r'"([^"\\]|\\.)*"'),
        ('BOOL', r'\b(true|false)\b'),
        ('IF', r'\bif\b'),
        ('ELSE', r'\belse\b'),
        ('REPEAT', r'\brepeat\b'),
        ('WHILE', r'\bwhile\b'),
        ('FUNC', r'\bfunc\b'),
        ('RETURN', r'\breturn\b'),
        ('END', r'\bend\b'),
        ('LET', r'\blet\b'),
        ('PRINT', r'\bprint\b'),
        ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('EQ', r'=='),
        ('NEQ', r'!='),
        ('LTE', r'<='),
        ('GTE', r'>='),
        ('LT', r'<'),
        ('GT', r'>'),
        ('ASSIGN', r'='),
        ('PLUS', r'\+'),
        ('MINUS', r'-'),
        ('MULT', r'\*'),
        ('DIV', r'/'),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('COMMA', r','),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]+'),
        ('COMMENT', r'#[^\n]*'),
    ]
    
    def __init__(self, code: str):
        self.code = code
        self.pos = 0
        self.line = 1
        self.tokens = []
        
    def tokenize(self) -> List[tuple]:
        while self.pos < len(self.code):
            matched = False
            for token_type, pattern in self.TOKEN_PATTERNS:
                regex = re.compile(pattern)
                match = regex.match(self.code, self.pos)
                if match:
                    value = match.group(0)
                    if token_type not in ('SKIP', 'COMMENT'):
                        if token_type == 'NEWLINE':
                            self.tokens.append((token_type, value, self.line))
                            self.line += 1
                        else:
                            self.tokens.append((token_type, value, self.line))
                    elif token_type == 'COMMENT':
                        pass
                    self.pos = match.end()
                    matched = True
                    break
            
            if not matched:
                raise MuxError(f"❌ Carácter inesperado '{self.code[self.pos]}' en línea {self.line}")
        
        return self.tokens

class Parser:
    """Analizador sintáctico para Mux"""
    
    def __init__(self, tokens: List[tuple]):
        self.tokens = [t for t in tokens if t[0] != 'NEWLINE']
        self.pos = 0
        
    def current(self) -> Optional[tuple]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    
    def advance(self):
        self.pos += 1
        
    def expect(self, token_type: str) -> tuple:
        token = self.current()
        if not token or token[0] != token_type:
            line = token[2] if token else "EOF"
            raise MuxError(f"❌ Se esperaba {token_type} en línea {line}")
        self.advance()
        return token
    
    def parse(self) -> List[Any]:
        statements = []
        while self.current():
            statements.append(self.parse_statement())
        return statements
    
    def parse_statement(self):
        token = self.current()
        if not token:
            return None
            
        if token[0] == 'LET':
            return self.parse_let()
        elif token[0] == 'PRINT':
            return self.parse_print()
        elif token[0] == 'IF':
            return self.parse_if()
        elif token[0] == 'REPEAT':
            return self.parse_repeat()
        elif token[0] == 'WHILE':
            return self.parse_while()
        elif token[0] == 'FUNC':
            return self.parse_func()
        elif token[0] == 'RETURN':
            return self.parse_return()
        elif token[0] == 'ID':
            next_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_token and next_token[0] == 'ASSIGN':
                return self.parse_assignment()
            elif next_token and next_token[0] == 'LPAREN':
                return self.parse_call()
        
        raise MuxError(f"❌ Declaración no reconocida en línea {token[2]}")

    def parse_let(self):
        self.advance()
        name = self.expect('ID')[1]
        self.expect('ASSIGN')
        value = self.parse_expression()
        return ('let', name, value)
    
    def parse_assignment(self):
        name = self.expect('ID')[1]
        self.expect('ASSIGN')
        value = self.parse_expression()
        return ('assign', name, value)
    
    def parse_print(self):
        self.advance()
        self.expect('LPAREN')
        expr = self.parse_expression()
        self.expect('RPAREN')
        return ('print', expr)
    
    def parse_if(self):
        self.advance()
        condition = self.parse_expression()
        body = []
        while self.current() and self.current()[0] not in ('ELSE', 'END'):
            body.append(self.parse_statement())
        
        else_body = []
        if self.current() and self.current()[0] == 'ELSE':
            self.advance()
            while self.current() and self.current()[0] != 'END':
                else_body.append(self.parse_statement())
        
        self.expect('END')
        return ('if', condition, body, else_body)
    
    def parse_repeat(self):
        self.advance()
        times = self.parse_expression()
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('repeat', times, body)
    
    def parse_while(self):
        self.advance()
        condition = self.parse_expression()
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('while', condition, body)
    
    def parse_func(self):
        self.advance()
        name = self.expect('ID')[1]
        self.expect('LPAREN')
        params = []
        if self.current() and self.current()[0] == 'ID':
            params.append(self.expect('ID')[1])
            while self.current() and self.current()[0] == 'COMMA':
                self.advance()
                params.append(self.expect('ID')[1])
        self.expect('RPAREN')
        
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('func', name, params, body)
    
    def parse_return(self):
        self.advance()
        value = self.parse_expression() if self.current() and self.current()[0] != 'END' else None
        return ('return', value)
    
    def parse_call(self):
        name = self.expect('ID')[1]
        self.expect('LPAREN')
        args = []
        if self.current() and self.current()[0] != 'RPAREN':
            args.append(self.parse_expression())
            while self.current() and self.current()[0] == 'COMMA':
                self.advance()
                args.append(self.parse_expression())
        self.expect('RPAREN')
        return ('call', name, args)
    
    def parse_expression(self):
        return self.parse_comparison()
    
    def parse_comparison(self):
        left = self.parse_additive()
        
        while self.current() and self.current()[0] in ('EQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE'):
            op = self.current()[0]
            self.advance()
            right = self.parse_additive()
            left = ('binop', op, left, right)
        
        return left
    
    def parse_additive(self):
        left = self.parse_multiplicative()
        
        while self.current() and self.current()[0] in ('PLUS', 'MINUS'):
            op = self.current()[0]
            self.advance()
            right = self.parse_multiplicative()
            left = ('binop', op, left, right)
        
        return left
    
    def parse_multiplicative(self):
        left = self.parse_primary()
        
        while self.current() and self.current()[0] in ('MULT', 'DIV'):
            op = self.current()[0]
            self.advance()
            right = self.parse_primary()
            left = ('binop', op, left, right)
        
        return left
    
    def parse_primary(self):
        token = self.current()
        
        if token[0] == 'NUMBER':
            self.advance()
            return ('number', float(token[1]) if '.' in token[1] else int(token[1]))
        elif token[0] == 'STRING':
            self.advance()
            return ('string', token[1][1:-1])
        elif token[0] == 'BOOL':
            self.advance()
            return ('bool', token[1] == 'true')
        elif token[0] == 'ID':
            next_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_token and next_token[0] == 'LPAREN':
                return self.parse_call()
            self.advance()
            return ('var', token[1])
        elif token[0] == 'LPAREN':
            self.advance()
            expr = self.parse_expression()
            self.expect('RPAREN')
            return expr
        
        raise MuxError(f"❌ Expresión no válida en línea {token[2]}")

class Interpreter:
    """Intérprete de Mux"""
    
    def __init__(self):
        self.globals = {}
        self.locals_stack = []
        
    def run(self, ast: List[Any]):
        try:
            for statement in ast:
                result = self.eval_statement(statement)
                if result and result[0] == 'return':
                    return result[1]
        except MuxError as e:
            print(f"\n{e}")
            sys.exit(1)
    
    def eval_statement(self, stmt):
        if not stmt:
            return None
            
        stmt_type = stmt[0]
        
        if stmt_type == 'let':
            _, name, value = stmt
            val = self.eval_expression(value)
            self.set_var(name, val)
        
        elif stmt_type == 'assign':
            _, name, value = stmt
            val = self.eval_expression(value)
            self.set_var(name, val)
        
        elif stmt_type == 'print':
            _, expr = stmt
            val = self.eval_expression(expr)
            print(val)
        
        elif stmt_type == 'if':
            _, condition, body, else_body = stmt
            if self.eval_expression(condition):
                for s in body:
                    result = self.eval_statement(s)
                    if result and result[0] == 'return':
                        return result
            else:
                for s in else_body:
                    result = self.eval_statement(s)
                    if result and result[0] == 'return':
                        return result
        
        elif stmt_type == 'repeat':
            _, times_expr, body = stmt
            times = self.eval_expression(times_expr)
            if not isinstance(times, int):
                raise MuxError("❌ repeat requiere un número entero")
            for _ in range(times):
                for s in body:
                    result = self.eval_statement(s)
                    if result and result[0] == 'return':
                        return result
        
        elif stmt_type == 'while':
            _, condition, body = stmt
            while self.eval_expression(condition):
                for s in body:
                    result = self.eval_statement(s)
                    if result and result[0] == 'return':
                        return result
        
        elif stmt_type == 'func':
            _, name, params, body = stmt
            self.set_var(name, ('function', params, body))
        
        elif stmt_type == 'return':
            _, value = stmt
            return ('return', self.eval_expression(value) if value else None)
        
        elif stmt_type == 'call':
            return self.eval_expression(stmt)
        
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
            for stmt in body:
                ret = self.eval_statement(stmt)
                if ret and ret[0] == 'return':
                    result = ret[1]
                    break
            self.locals_stack.pop()
            return result
        
        return None
    
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

def main():
    if len(sys.argv) < 2:
        print("Uso: python mux.py <archivo.mux>")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"❌ Archivo '{filename}' no encontrado")
        sys.exit(1)
    
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        interpreter = Interpreter()
        interpreter.run(ast)
        
    except MuxError as e:
        print(f"\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
