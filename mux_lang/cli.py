"""
Mux CLI - Interfaz de Línea de Comandos
Creador: MushhX
"""

import sys
import os
from .lexer import Lexer, MuxError
from .parser import Parser
from .interpreter import Interpreter

def main():
    if len(sys.argv) < 2:
        print("Mux Programming Language v1.0.0")
        print("Creador: MushhX")
        print("\nUso:")
        print("  mux <archivo.mux>        - Ejecutar un archivo")
        print("  mux --version            - Ver versión")
        print("  mux --help               - Ver ayuda")
        sys.exit(1)
    
    if sys.argv[1] == '--version':
        print("Mux v1.0.0")
        print("Creador: MushhX")
        sys.exit(0)
    
    if sys.argv[1] == '--help':
        print("Mux Programming Language")
        print("Creador: MushhX")
        print("\nUso: mux <archivo.mux>")
        print("\nOpciones:")
        print("  --version    Ver versión")
        print("  --help       Ver ayuda")
        print("\nEjemplos:")
        print("  mux hola.mux")
        print("  mux ejemplos/calculadora.mux")
        sys.exit(0)
    
    filename = sys.argv[1]
    
    if not os.path.exists(filename):
        print(f"❌ Archivo '{filename}' no encontrado")
        sys.exit(1)
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")
        sys.exit(1)
    
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        interpreter = Interpreter()
        interpreter.run(ast, filename)
        
    except MuxError as e:
        print(f"\n{e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Ejecución interrumpida")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
