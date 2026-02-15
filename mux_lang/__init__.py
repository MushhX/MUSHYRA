"""
Mux Programming Language
Creador: MushhX
Un lenguaje moderno, accesible y ligero
"""

__version__ = '1.0.0'
__author__ = 'MushhX'

from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser

__all__ = ['Interpreter', 'Lexer', 'Parser']
