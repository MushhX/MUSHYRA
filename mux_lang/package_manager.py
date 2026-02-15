"""
Mux Package Manager
Creador: MushhX
Gestor de paquetes para Mux
"""

import os
import sys
import json
import shutil
from pathlib import Path

PACKAGES_DIR = Path.home() / '.mux' / 'packages'
REGISTRY_FILE = Path.home() / '.mux' / 'registry.json'

def init_package_system():
    """Inicializar sistema de paquetes"""
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, 'w') as f:
            json.dump({}, f)

def list_packages():
    """Listar paquetes instalados"""
    init_package_system()
    
    if not REGISTRY_FILE.exists():
        print("No hay paquetes instalados")
        return
    
    with open(REGISTRY_FILE, 'r') as f:
        registry = json.load(f)
    
    if not registry:
        print("No hay paquetes instalados")
        return
    
    print("📦 Paquetes instalados:\n")
    for name, info in registry.items():
        version = info.get('version', '1.0.0')
        description = info.get('description', 'Sin descripción')
        print(f"  {name} ({version})")
        print(f"    {description}\n")

def install_package(package_name: str):
    """Instalar un paquete"""
    init_package_system()
    
    print(f"📦 Instalando {package_name}...")
    
    # Aquí iría la lógica para descargar desde un repositorio
    # Por ahora, solo simulamos la instalación
    
    with open(REGISTRY_FILE, 'r') as f:
        registry = json.load(f)
    
    registry[package_name] = {
        'version': '1.0.0',
        'description': f'Paquete {package_name}',
        'installed_at': str(Path.cwd())
    }
    
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"✅ {package_name} instalado correctamente")

def uninstall_package(package_name: str):
    """Desinstalar un paquete"""
    init_package_system()
    
    with open(REGISTRY_FILE, 'r') as f:
        registry = json.load(f)
    
    if package_name not in registry:
        print(f"❌ Paquete {package_name} no está instalado")
        return
    
    del registry[package_name]
    
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"✅ {package_name} desinstalado correctamente")

def main():
    if len(sys.argv) < 2:
        print("Mux Package Manager")
        print("Creador: MushhX")
        print("\nUso:")
        print("  mux-pkg list              - Listar paquetes")
        print("  mux-pkg install <paquete> - Instalar paquete")
        print("  mux-pkg remove <paquete>  - Desinstalar paquete")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'list':
        list_packages()
    elif command == 'install':
        if len(sys.argv) < 3:
            print("❌ Especifica el nombre del paquete")
            sys.exit(1)
        install_package(sys.argv[2])
    elif command == 'remove' or command == 'uninstall':
        if len(sys.argv) < 3:
            print("❌ Especifica el nombre del paquete")
            sys.exit(1)
        uninstall_package(sys.argv[2])
    else:
        print(f"❌ Comando '{command}' no reconocido")
        sys.exit(1)

if __name__ == '__main__':
    main()
