"""
Script para crear un instalador portable de Mux (sin Inno Setup)
Creador: MushhX

Crea un archivo ZIP con todo lo necesario para usar Mux
"""

import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

def create_portable_installer():
    """Crear instalador portable"""
    
    print("📦 Creando instalador portable de Mux...")
    print("   Creador: MushhX\n")
    
    # Verificar que existe el ejecutable
    if not os.path.exists("dist/mux.exe"):
        print("❌ No se encontró dist/mux.exe")
        print("   Ejecuta primero: python build_exe.py")
        return False
    
    print("✅ Ejecutable encontrado")
    
    # Crear carpeta temporal
    temp_dir = "mux_portable_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    print("📁 Preparando archivos...")
    
    # Copiar ejecutable
    shutil.copy("dist/mux.exe", f"{temp_dir}/mux.exe")
    print("  ✓ Ejecutable")
    
    # Copiar librería estándar
    if os.path.exists("mux_lang/stdlib"):
        shutil.copytree("mux_lang/stdlib", f"{temp_dir}/mux_lang/stdlib")
        print("  ✓ Librería estándar")
    
    # Copiar ejemplos
    if os.path.exists("examples"):
        shutil.copytree("examples", f"{temp_dir}/examples")
        print("  ✓ Ejemplos")
    
    # Copiar documentación
    docs = [
        "README.md",
        "LICENSE",
        "QUICKSTART.md",
        "FEATURES.md",
        "STDLIB_REFERENCE.md",
        "UNIQUE_COMMANDS.md",
        "EXECUTABLE_GUIDE.md"
    ]
    
    for doc in docs:
        if os.path.exists(doc):
            shutil.copy(doc, f"{temp_dir}/{doc}")
    print("  ✓ Documentación")
    
    # Crear archivo de instalación
    install_txt = """Mux Programming Language v1.0.0
Creador: MushhX

=== INSTALACIÓN ===

Este es un instalador portable. No requiere instalación tradicional.

OPCIÓN 1: Usar desde esta carpeta
  1. Abre una terminal (CMD o PowerShell)
  2. Navega a esta carpeta
  3. Ejecuta: mux.exe programa.mux

OPCIÓN 2: Agregar al PATH
  1. Copia esta carpeta a una ubicación permanente (ej: C:\\Mux)
  2. Agrega la ruta al PATH del sistema:
     - Windows 10/11: Busca "variables de entorno" en el menú inicio
     - Edita la variable "Path" del usuario
     - Agrega la ruta donde copiaste Mux
  3. Reinicia la terminal
  4. Ahora puedes usar: mux programa.mux desde cualquier lugar

OPCIÓN 3: Copiar a carpeta del sistema
  1. Copia mux.exe a C:\\Windows\\System32
  2. Ahora puedes usar: mux programa.mux desde cualquier lugar
  (Requiere permisos de administrador)

=== PRIMEROS PASOS ===

1. Abre la carpeta "examples"
2. Ejecuta: mux.exe examples\\hola_mundo.mux
3. Lee README.md para más información

=== DOCUMENTACIÓN ===

- README.md - Documentación principal
- QUICKSTART.md - Inicio rápido
- FEATURES.md - Características completas
- STDLIB_REFERENCE.md - Referencia de librería estándar
- UNIQUE_COMMANDS.md - Comandos únicos
- EXECUTABLE_GUIDE.md - Guía del ejecutable

=== SOPORTE ===

GitHub: https://github.com/mushhx/mux
Issues: https://github.com/mushhx/mux/issues

=== LICENCIA ===

MIT License - Ver LICENSE

¡Disfruta programando con Mux! 🌍⚙️
"""
    
    with open(f"{temp_dir}/INSTALL.txt", "w", encoding="utf-8") as f:
        f.write(install_txt)
    print("  ✓ Instrucciones de instalación")
    
    # Crear archivo de versión
    version_txt = f"""Mux Programming Language
Version: 1.0.0
Build Date: {datetime.now().strftime('%Y-%m-%d')}
Platform: Windows x64
Creador: MushhX

Contenido:
- mux.exe (7.89 MB)
- Librería estándar (15 módulos)
- Ejemplos (20+ archivos)
- Documentación completa
"""
    
    with open(f"{temp_dir}/VERSION.txt", "w", encoding="utf-8") as f:
        f.write(version_txt)
    print("  ✓ Información de versión")
    
    # Crear archivo ZIP
    zip_name = f"mux-portable-v1.0.0-windows-x64.zip"
    print(f"\n📦 Creando archivo ZIP: {zip_name}")
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, f"mux/{arcname}")
    
    # Limpiar carpeta temporal
    shutil.rmtree(temp_dir)
    
    # Obtener tamaño del ZIP
    zip_size = os.path.getsize(zip_name) / (1024 * 1024)
    
    print(f"\n✅ ¡Instalador portable creado exitosamente!")
    print(f"\n📦 Archivo: {zip_name}")
    print(f"📏 Tamaño: {zip_size:.2f} MB")
    print(f"\n📋 Contenido:")
    print(f"  • Ejecutable de Mux (7.89 MB)")
    print(f"  • Librería estándar (15 módulos)")
    print(f"  • Ejemplos (20+ archivos)")
    print(f"  • Documentación completa")
    print(f"  • Instrucciones de instalación")
    print(f"\n🚀 Para usar:")
    print(f"  1. Extrae el archivo ZIP")
    print(f"  2. Lee INSTALL.txt para instrucciones")
    print(f"  3. Ejecuta: mux.exe examples\\hola_mundo.mux")
    print(f"\n💡 Este instalador portable puede ser distribuido sin necesidad de Inno Setup")
    
    return True

if __name__ == '__main__':
    create_portable_installer()
