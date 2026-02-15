"""
Script para compilar Mux a ejecutable
Creador: MushhX

Uso:
    python build_exe.py
"""

import os
import sys
import subprocess

def build_executable():
    print("🔨 Compilando Mux a ejecutable...")
    print("   Creador: MushhX\n")
    
    # Verificar que PyInstaller esté instalado
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller no está instalado")
        print("   Instala con: pip install pyinstaller")
        sys.exit(1)
    
    # Crear archivo principal para PyInstaller
    main_content = """
import sys
from mux_lang.cli import main

if __name__ == '__main__':
    main()
"""
    
    with open('mux_main.py', 'w', encoding='utf-8') as f:
        f.write(main_content)
    
    # Comando de PyInstaller
    cmd = [
        'pyinstaller',
        '--onefile',
        '--name=mux',
        '--clean',
        '--add-data=mux_lang/stdlib:mux_lang/stdlib',
        'mux_main.py'
    ]
    
    print("Ejecutando PyInstaller...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("\n✅ ¡Compilación exitosa!")
        print(f"   Ejecutable creado en: dist/mux{'.exe' if sys.platform == 'win32' else ''}")
        print("\nPuedes usar el ejecutable así:")
        print(f"   ./dist/mux{'.exe' if sys.platform == 'win32' else ''} ejemplos/hola_mundo.mux")
    else:
        print("\n❌ Error en la compilación:")
        print(result.stderr)
        sys.exit(1)
    
    # Limpiar archivo temporal
    if os.path.exists('mux_main.py'):
        os.remove('mux_main.py')

if __name__ == '__main__':
    build_executable()
