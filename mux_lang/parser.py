"""
Mux Parser - Analizador Sintáctico
Creador: MushhX
"""

from typing import Any, List, Optional, Tuple
from .lexer import MuxError

class Parser:
    """Analizador sintáctico para Mux"""
    
    def __init__(self, tokens: List[Tuple]):
        self.tokens = [t for t in tokens if t[0] != 'NEWLINE']
        self.pos = 0
        
    def current(self) -> Optional[Tuple]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    
    def peek(self, offset: int = 1) -> Optional[Tuple]:
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else None
    
    def advance(self):
        self.pos += 1
        
    def expect(self, token_type: str) -> Tuple:
        token = self.current()
        if not token or token[0] != token_type:
            line = token[2] if token else "EOF"
            raise MuxError(f"❌ Se esperaba {token_type} en línea {line}")
        self.advance()
        return token
    
    def parse(self) -> List[Any]:
        statements = []
        while self.current():
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        return statements
    
    def parse_statement(self):
        token = self.current()
        if not token:
            return None
            
        if token[0] == 'IMPORT':
            return self.parse_import()
        elif token[0] == 'FROM':
            return self.parse_from_import()
        elif token[0] == 'LET':
            return self.parse_let()
        elif token[0] == 'PRINT':
            return self.parse_print()
        elif token[0] == 'IF':
            return self.parse_if()
        elif token[0] == 'REPEAT':
            return self.parse_repeat()
        elif token[0] == 'WHILE':
            return self.parse_while()
        elif token[0] == 'FOR':
            return self.parse_for()
        elif token[0] == 'FUNC':
            return self.parse_func()
        elif token[0] == 'RETURN':
            return self.parse_return()
        elif token[0] == 'BREAK':
            self.advance()
            return ('break',)
        elif token[0] == 'CONTINUE':
            self.advance()
            return ('continue',)
        elif token[0] == 'ASSERT':
            return self.parse_assert()
        elif token[0] == 'SHOW':
            return self.parse_show()
        elif token[0] == 'ASK':
            return self.parse_ask()
        elif token[0] == 'SAY':
            return self.parse_say()
        elif token[0] == 'WAIT':
            return self.parse_wait()
        elif token[0] == 'EXIT':
            return self.parse_exit()
        elif token[0] == 'PASS':
            self.advance()
            return ('pass',)
        elif token[0] == 'LOOP':
            return self.parse_loop()
        elif token[0] == 'TIMES':
            return self.parse_times()
        elif token[0] == 'UNTIL':
            return self.parse_until()
        elif token[0] == 'UNLESS':
            return self.parse_unless()
        elif token[0] == 'EACH':
            return self.parse_each()
        elif token[0] == 'ID':
            next_token = self.peek()
            if next_token and next_token[0] == 'ASSIGN':
                return self.parse_assignment()
            elif next_token and next_token[0] == 'LPAREN':
                return self.parse_call()
            elif next_token and next_token[0] == 'DOT':
                # Método o acceso a atributo
                return ('expr_stmt', self.parse_expression())
            elif next_token and next_token[0] == 'LBRACKET':
                # Verificar si es asignación o solo acceso
                saved_pos = self.pos
                self.advance()  # ID
                self.advance()  # [
                # Buscar el ]
                depth = 1
                while self.current() and depth > 0:
                    if self.current()[0] == 'LBRACKET':
                        depth += 1
                    elif self.current()[0] == 'RBRACKET':
                        depth -= 1
                    self.advance()
                # Verificar si hay =
                if self.current() and self.current()[0] == 'ASSIGN':
                    self.pos = saved_pos
                    return self.parse_index_assignment()
                else:
                    self.pos = saved_pos
                    return ('expr_stmt', self.parse_expression())
        
        raise MuxError(f"❌ Declaración no reconocida en línea {token[2]}")
    
    def parse_import(self):
        self.advance()
        module = self.expect('ID')[1]
        alias = None
        if self.current() and self.current()[0] == 'AS':
            self.advance()
            alias = self.expect('ID')[1]
        return ('import', module, alias)
    
    def parse_from_import(self):
        self.advance()
        module = self.expect('ID')[1]
        self.expect('IMPORT')
        items = [self.expect('ID')[1]]
        while self.current() and self.current()[0] == 'COMMA':
            self.advance()
            items.append(self.expect('ID')[1])
        return ('from_import', module, items)
    
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
    
    def parse_index_assignment(self):
        name = self.expect('ID')[1]
        self.expect('LBRACKET')
        index = self.parse_expression()
        self.expect('RBRACKET')
        self.expect('ASSIGN')
        value = self.parse_expression()
        return ('index_assign', name, index, value)
    
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
        while self.current() and self.current()[0] not in ('ELSE', 'ELIF', 'END'):
            body.append(self.parse_statement())
        
        elif_branches = []
        while self.current() and self.current()[0] == 'ELIF':
            self.advance()
            elif_cond = self.parse_expression()
            elif_body = []
            while self.current() and self.current()[0] not in ('ELSE', 'ELIF', 'END'):
                elif_body.append(self.parse_statement())
            elif_branches.append((elif_cond, elif_body))
        
        else_body = []
        if self.current() and self.current()[0] == 'ELSE':
            self.advance()
            while self.current() and self.current()[0] != 'END':
                else_body.append(self.parse_statement())
        
        self.expect('END')
        return ('if', condition, body, elif_branches, else_body)
    
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
    
    def parse_for(self):
        self.advance()
        var = self.expect('ID')[1]
        self.expect('IN')
        iterable = self.parse_expression()
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('for', var, iterable, body)
    
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
    
    def parse_method_call(self):
        obj = self.expect('ID')[1]
        methods = []
        
        while self.current() and self.current()[0] == 'DOT':
            self.expect('DOT')
            method = self.expect('ID')[1]
            self.expect('LPAREN')
            args = []
            if self.current() and self.current()[0] != 'RPAREN':
                args.append(self.parse_expression())
                while self.current() and self.current()[0] == 'COMMA':
                    self.advance()
                    args.append(self.parse_expression())
            self.expect('RPAREN')
            methods.append((method, args))
        
        # Si solo hay un método, devolver formato simple
        if len(methods) == 1:
            return ('method_call', obj, methods[0][0], methods[0][1])
        
        # Si hay múltiples, encadenar
        return ('chained_method_call', obj, methods)
    
    def parse_expression(self):
        return self.parse_logical_or()
    
    def parse_logical_or(self):
        left = self.parse_logical_and()
        while self.current() and self.current()[0] == 'OR':
            self.advance()
            right = self.parse_logical_and()
            left = ('binop', 'OR', left, right)
        return left
    
    def parse_logical_and(self):
        left = self.parse_comparison()
        while self.current() and self.current()[0] == 'AND':
            self.advance()
            right = self.parse_comparison()
            left = ('binop', 'AND', left, right)
        return left
    
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
        left = self.parse_unary()
        while self.current() and self.current()[0] in ('MULT', 'DIV', 'MOD'):
            op = self.current()[0]
            self.advance()
            right = self.parse_unary()
            left = ('binop', op, left, right)
        return left
    
    def parse_unary(self):
        if self.current() and self.current()[0] == 'NOT':
            self.advance()
            expr = self.parse_unary()
            return ('unary', 'NOT', expr)
        elif self.current() and self.current()[0] == 'MINUS':
            self.advance()
            expr = self.parse_unary()
            return ('unary', 'MINUS', expr)
        return self.parse_postfix()
    
    def parse_postfix(self):
        expr = self.parse_primary()
        
        while self.current():
            if self.current()[0] == 'LBRACKET':
                self.advance()
                index = self.parse_expression()
                self.expect('RBRACKET')
                expr = ('index', expr, index)
            elif self.current()[0] == 'DOT':
                self.advance()
                attr = self.expect('ID')[1]
                if self.current() and self.current()[0] == 'LPAREN':
                    self.advance()
                    args = []
                    if self.current() and self.current()[0] != 'RPAREN':
                        args.append(self.parse_expression())
                        while self.current() and self.current()[0] == 'COMMA':
                            self.advance()
                            args.append(self.parse_expression())
                    self.expect('RPAREN')
                    expr = ('method', expr, attr, args)
                else:
                    expr = ('attr', expr, attr)
            else:
                break
        
        return expr
    
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
        elif token[0] == 'LBRACKET':
            return self.parse_list()
        elif token[0] == 'LBRACE':
            return self.parse_dict()
        elif token[0] in ('INPUT', 'LEN', 'TYPE', 'STR', 'INT', 'FLOAT', 'RANGE'):
            return self.parse_builtin()
        elif token[0] == 'ID':
            next_token = self.peek()
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
    
    def parse_list(self):
        self.expect('LBRACKET')
        elements = []
        if self.current() and self.current()[0] != 'RBRACKET':
            elements.append(self.parse_expression())
            while self.current() and self.current()[0] == 'COMMA':
                self.advance()
                if self.current() and self.current()[0] == 'RBRACKET':
                    break
                elements.append(self.parse_expression())
        self.expect('RBRACKET')
        return ('list', elements)
    
    def parse_dict(self):
        self.expect('LBRACE')
        pairs = []
        if self.current() and self.current()[0] != 'RBRACE':
            key = self.parse_expression()
            self.expect('COLON')
            value = self.parse_expression()
            pairs.append((key, value))
            while self.current() and self.current()[0] == 'COMMA':
                self.advance()
                if self.current() and self.current()[0] == 'RBRACE':
                    break
                key = self.parse_expression()
                self.expect('COLON')
                value = self.parse_expression()
                pairs.append((key, value))
        self.expect('RBRACE')
        return ('dict', pairs)
    
    def parse_builtin(self):
        name = self.current()[0]
        self.advance()
        self.expect('LPAREN')
        args = []
        if self.current() and self.current()[0] != 'RPAREN':
            args.append(self.parse_expression())
            while self.current() and self.current()[0] == 'COMMA':
                self.advance()
                args.append(self.parse_expression())
        self.expect('RPAREN')
        return ('builtin', name.lower(), args)

    def parse_assert(self):
        self.advance()
        self.expect('LPAREN')
        condition = self.parse_expression()
        message = None
        if self.current() and self.current()[0] == 'COMMA':
            self.advance()
            message = self.parse_expression()
        self.expect('RPAREN')
        return ('assert', condition, message)
    
    def parse_show(self):
        self.advance()
        self.expect('LPAREN')
        expr = self.parse_expression()
        self.expect('RPAREN')
        return ('show', expr)
    
    def parse_ask(self):
        self.advance()
        self.expect('LPAREN')
        prompt = self.parse_expression()
        self.expect('RPAREN')
        return ('ask', prompt)
    
    def parse_say(self):
        self.advance()
        self.expect('LPAREN')
        message = self.parse_expression()
        self.expect('RPAREN')
        return ('say', message)
    
    def parse_wait(self):
        self.advance()
        self.expect('LPAREN')
        seconds = self.parse_expression()
        self.expect('RPAREN')
        return ('wait', seconds)
    
    def parse_exit(self):
        self.advance()
        code = None
        if self.current() and self.current()[0] != 'END':
            code = self.parse_expression()
        return ('exit', code)
    
    def parse_loop(self):
        self.advance()
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('loop', body)
    
    def parse_times(self):
        # N times do ... end
        # Buscar hacia atrás el número
        return ('times', 5, [])
    
    def parse_until(self):
        self.advance()
        condition = self.parse_expression()
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('until', condition, body)
    
    def parse_unless(self):
        self.advance()
        condition = self.parse_expression()
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('unless', condition, body)
    
    def parse_each(self):
        self.advance()
        var = self.expect('ID')[1]
        self.expect('IN')
        iterable = self.parse_expression()
        body = []
        while self.current() and self.current()[0] != 'END':
            body.append(self.parse_statement())
        self.expect('END')
        return ('each', var, iterable, body)
