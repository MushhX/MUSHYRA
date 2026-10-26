"""
Mux Programming Language
Creador: MushhX
Un lenguaje moderno, accesible y ligero
"""

from ._version import __version__
__author__ = 'MushhX'

from .interpreter import Interpreter
from .lexer import Lexer, MuxError, Token
from .parser import Parser

__all__ = ['Interpreter', 'Lexer', 'MuxError', 'Parser', 'Token', '__version__']
