"""
Script para construir el instalador de Mux
Creador: MushhX

Requiere Inno Setup instalado en Windows
Descarga desde: https://jrsoftware.org/isdl.php
"""

import os
import sys
import subprocess
from pathlib import Path

def find_inno_setup():
    """Buscar instalación de Inno Setup"""
    
    # Rutas comunes de Inno Setup
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def check_requirements():
    """Verificar que todo esté listo"""
    
    print("🔍 Verificando requisitos...")
    
    # Verificar que existe el ejecutable
    if not os.path.exists("dist/mux.exe"):
        print("❌ No se encontró dist/mux.exe")
        print("   Ejecuta primero: python build_exe.py")
        return False
    
    print("✅ Ejecutable encontrado")
    
    # Verificar que existe el script de Inno Setup
    if not os.path.exists("installer.iss"):
        print("❌ No se encontró installer.iss")
        return False
    
    print("✅ Script de instalador encontrado")
    
    # Verificar icono
    if not os.path.exists("mux_icon.ico"):
        print("⚠️ No se encontró mux_icon.ico")
        print("   Creando icono...")
        try:
            subprocess.run([sys.executable, "create_icon.py"], check=True)
        except:
            print("   No se pudo crear el icono automáticamente")
            print("   El instalador se creará sin icono personalizado")
    else:
        print("✅ Icono encontrado")
    
    return True

def build_installer():
    """Construir el instalador"""
    
    print("\n🔨 Construyendo instalador de Mux...")
    print("   Creador: MushhX\n")
    
    # Verificar requisitos
    if not check_requirements():
        sys.exit(1)
    
    # Buscar Inno Setup
    iscc_path = find_inno_setup()
    
    if not iscc_path:
        print("\n❌ Inno Setup no está instalado")
        print("\nPara instalar Inno Setup:")
        print("1. Descarga desde: https://jrsoftware.org/isdl.php")
        print("2. Instala Inno Setup")
        print("3. Ejecuta este script nuevamente")
        print("\nAlternativamente, puedes abrir installer.iss con Inno Setup manualmente")
        sys.exit(1)
    
    print(f"✅ Inno Setup encontrado: {iscc_path}\n")
    
    # Crear carpeta de salida
    os.makedirs("installer_output", exist_ok=True)
    
    # Compilar instalador
    print("Compilando instalador...")
    try:
        result = subprocess.run(
            [iscc_path, "installer.iss"],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(result.stdout)
        
        print("\n✅ ¡Instalador creado exitosamente!")
        print(f"\n📦 Instalador creado en: installer_output\\mux-setup-1.0.0.exe")
        print("\nPuedes distribuir este instalador a otros usuarios.")
        print("El instalador incluye:")
        print("  • Ejecutable de Mux (7.89 MB)")
        print("  • Librería estándar (15 módulos)")
        print("  • Ejemplos (20+ archivos)")
        print("  • Documentación completa")
        print("\nCaracterísticas del instalador:")
        print("  • Instalación en Program Files")
        print("  • Opción de agregar al PATH")
        print("  • Accesos directos en menú inicio")
        print("  • Desinstalador incluido")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al compilar instalador:")
        print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build_installer()
