"""
Mux Lexer - Analizador Léxico
Creador: MushhX
"""

import re
from typing import List, Tuple

class MuxError(Exception):
    """Error base de Mux con mensajes comprensibles"""
    pass

class Lexer:
    """Analizador léxico para Mux"""
    
    TOKEN_PATTERNS = [
        ('NUMBER', r'\d+(\.\d+)?'),
        ('STRING', r'"([^"\\]|\\.)*"'),
        ('BOOL', r'\b(true|false)\b'),
        ('IMPORT', r'\bimport\b'),
        ('FROM', r'\bfrom\b'),
        ('AS', r'\bas\b'),
        ('IF', r'\bif\b'),
        ('ELSE', r'\belse\b'),
        ('ELIF', r'\belif\b'),
        ('REPEAT', r'\brepeat\b'),
        ('WHILE', r'\bwhile\b'),
        ('FOR', r'\bfor\b'),
        ('IN', r'\bin\b'),
        ('FUNC', r'\bfunc\b'),
        ('RETURN', r'\breturn\b'),
        ('BREAK', r'\bbreak\b'),
        ('CONTINUE', r'\bcontinue\b'),
        ('END', r'\bend\b'),
        ('LET', r'\blet\b'),
        ('PRINT', r'\bprint\b'),
        ('INPUT', r'\binput\b'),
        ('LEN', r'\blen\b'),
        ('TYPE', r'\btype\b'),
        ('STR', r'\bstr\b'),
        ('INT', r'\bint\b'),
        ('FLOAT', r'\bfloat\b'),
        ('RANGE', r'\brange\b'),
        ('ASSERT', r'\bassert\b'),
        ('TRY', r'\btry\b'),
        ('CATCH', r'\bcatch\b'),
        ('FINALLY', r'\bfinally\b'),
        ('THROW', r'\bthrow\b'),
        ('MATCH', r'\bmatch\b'),
        ('CASE', r'\bcase\b'),
        ('DEFAULT', r'\bdefault\b'),
        ('ASYNC', r'\basync\b'),
        ('AWAIT', r'\bawait\b'),
        ('YIELD', r'\byield\b'),
        ('WITH', r'\bwith\b'),
        ('CLASS', r'\bclass\b'),
        ('NEW', r'\bnew\b'),
        ('THIS', r'\bthis\b'),
        ('SUPER', r'\bsuper\b'),
        ('STATIC', r'\bstatic\b'),
        ('CONST', r'\bconst\b'),
        ('VAR', r'\bvar\b'),
        ('NULL', r'\bnull\b'),
        ('UNDEFINED', r'\bundefined\b'),
        ('TYPEOF', r'\btypeof\b'),
        ('INSTANCEOF', r'\binstanceof\b'),
        ('DELETE', r'\bdelete\b'),
        ('LAMBDA', r'\blambda\b'),
        ('MAP', r'\bmap\b'),
        ('FILTER', r'\bfilter\b'),
        ('REDUCE', r'\breduce\b'),
        ('EACH', r'\beach\b'),
        ('TIMES', r'\btimes\b'),
        ('UNTIL', r'\buntil\b'),
        ('UNLESS', r'\bunless\b'),
        ('WHEN', r'\bwhen\b'),
        ('THEN', r'\bthen\b'),
        ('DO', r'\bdo\b'),
        ('LOOP', r'\bloop\b'),
        ('EXIT', r'\bexit\b'),
        ('PASS', r'\bpass\b'),
        ('SHOW', r'\bshow\b'),
        ('ASK', r'\bask\b'),
        ('SAY', r'\bsay\b'),
        ('WAIT', r'\bwait\b'),
        ('RUN', r'\brun\b'),
        ('EXEC', r'\bexec\b'),
        ('EVAL', r'\beval\b'),
        ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('EQ', r'=='),
        ('NEQ', r'!='),
        ('LTE', r'<='),
        ('GTE', r'>='),
        ('LT', r'<'),
        ('GT', r'>'),
        ('AND', r'&&'),
        ('OR', r'\|\|'),
        ('NOT', r'!'),
        ('ASSIGN', r'='),
        ('PLUS', r'\+'),
        ('MINUS', r'-'),
        ('MULT', r'\*'),
        ('DIV', r'/'),
        ('MOD', r'%'),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACKET', r'\['),
        ('RBRACKET', r'\]'),
        ('LBRACE', r'\{'),
        ('RBRACE', r'\}'),
        ('COMMA', r','),
        ('DOT', r'\.'),
        ('COLON', r':'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]+'),
        ('COMMENT', r'#[^\n]*'),
    ]
    
    def __init__(self, code: str):
        self.code = code
        self.pos = 0
        self.line = 1
        self.tokens = []
        
    def tokenize(self) -> List[Tuple]:
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
                    self.pos = match.end()
                    matched = True
                    break
            
            if not matched:
                raise MuxError(f"❌ Carácter inesperado '{self.code[self.pos]}' en línea {self.line}")
        
        return self.tokens
