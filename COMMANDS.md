# Comandos Útiles de Mux
**Creador: MushhX**

## Comandos Básicos

### Ejecutar Programa
```bash
# Usando comando instalado
mux archivo.mux

# Usando módulo Python
python -m mux_lang.cli archivo.mux
```

### Ver Versión
```bash
mux --version
```

### Ver Ayuda
```bash
mux --help
```

## Gestor de Paquetes

### Listar Paquetes Instalados
```bash
mux-pkg list
```

### Instalar Paquete
```bash
mux-pkg install nombre_paquete
```

### Desinstalar Paquete
```bash
mux-pkg remove nombre_paquete
# o
mux-pkg uninstall nombre_paquete
```

## Instalación

### Instalar Mux
```bash
# Modo desarrollo (recomendado para desarrollo)
pip install -e .

# Instalación normal
pip install .

# Con características adicionales
pip install -e ".[web]"        # Para desarrollo web
pip install -e ".[discord]"    # Para bots de Discord
pip install -e ".[telegram]"   # Para bots de Telegram
pip install -e ".[whatsapp]"   # Para bots de WhatsApp
pip install -e ".[full]"       # Todas las características
```

### Desinstalar Mux
```bash
pip uninstall mux-lang
```

### Actualizar Mux
```bash
pip install -e . --upgrade
```

## Compilación

### Compilar a Ejecutable
```bash
# Instalar PyInstaller
pip install pyinstaller

# Compilar
python build_exe.py

# El ejecutable estará en dist/
```

### Usar Ejecutable
```bash
# Windows
dist\mux.exe archivo.mux

# Linux/macOS
./dist/mux archivo.mux
```

## Ejemplos

### Ejecutar Todos los Ejemplos Básicos
```bash
mux examples/hola_mundo.mux
mux examples/variables.mux
mux examples/condicionales.mux
mux examples/bucles.mux
mux examples/funciones.mux
mux examples/listas_y_diccionarios.mux
```

### Ejecutar Ejemplos de Aplicaciones
```bash
mux examples/calculadora.mux
mux examples/fibonacci.mux
mux examples/matematicas.mux
```

### Ejecutar Ejemplos Interactivos
```bash
# Estos requieren input del usuario
mux examples/todo_list.mux
mux examples/juego_adivinanza.mux
```

## Desarrollo

### Ejecutar en Modo Debug
```bash
# Añadir prints de debug en el código
python -m mux_lang.cli archivo.mux
```

### Ver Tokens (Debug)
```python
from mux_lang.lexer import Lexer

code = 'let x = 10'
lexer = Lexer(code)
tokens = lexer.tokenize()
print(tokens)
```

### Ver AST (Debug)
```python
from mux_lang.lexer import Lexer
from mux_lang.parser import Parser

code = 'let x = 10'
lexer = Lexer(code)
tokens = lexer.tokenize()
parser = Parser(tokens)
ast = parser.parse()
print(ast)
```

## Testing

### Probar Instalación
```bash
# Verificar que mux está instalado
which mux  # Linux/macOS
where mux  # Windows

# Verificar versión
mux --version

# Ejecutar ejemplo simple
mux examples/hola_mundo.mux
```

### Probar Todas las Características
```bash
# Variables y tipos
mux examples/variables.mux

# Condicionales
mux examples/condicionales.mux

# Bucles
mux examples/bucles.mux

# Funciones
mux examples/funciones.mux

# Listas y diccionarios
mux examples/listas_y_diccionarios.mux

# Módulos
mux examples/matematicas.mux

# Aplicaciones
mux examples/calculadora.mux
mux examples/fibonacci.mux
```

## Limpieza

### Limpiar Archivos de Compilación
```bash
# Windows
rmdir /s /q build dist mux_lang.egg-info __pycache__

# Linux/macOS
rm -rf build dist mux_lang.egg-info __pycache__
```

### Limpiar Caché de Python
```bash
# Windows
del /s /q *.pyc
rmdir /s /q __pycache__

# Linux/macOS
find . -type f -name '*.pyc' -delete
find . -type d -name '__pycache__' -delete
```

## Git

### Inicializar Repositorio
```bash
git init
git add .
git commit -m "Initial commit: Mux v1.0.0"
```

### Crear Repositorio en GitHub
```bash
git remote add origin https://github.com/mushhx/mux.git
git branch -M main
git push -u origin main
```

### Actualizar Repositorio
```bash
git add .
git commit -m "Descripción de cambios"
git push
```

## Distribución

### Crear Paquete para PyPI
```bash
# Instalar herramientas
pip install build twine

# Crear distribución
python -m build

# Subir a PyPI (test)
twine upload --repository testpypi dist/*

# Subir a PyPI (producción)
twine upload dist/*
```

### Instalar desde PyPI
```bash
# Una vez publicado
pip install mux-lang
```

## Documentación

### Ver Documentación
```bash
# README principal
cat README.md

# Inicio rápido
cat QUICKSTART.md

# Instalación
cat INSTALL.md

# Características
cat FEATURES.md

# Guía de bots
cat BOTS_GUIDE.md
```

### Generar Documentación HTML
```bash
# Usando markdown
pip install markdown
python -m markdown README.md > README.html
```

## Utilidades

### Contar Líneas de Código
```bash
# Linux/macOS
find mux_lang -name "*.py" | xargs wc -l

# Windows PowerShell
Get-ChildItem -Path mux_lang -Filter *.py -Recurse | Get-Content | Measure-Object -Line
```

### Buscar en Código
```bash
# Linux/macOS
grep -r "palabra" mux_lang/

# Windows PowerShell
Select-String -Path mux_lang\*.py -Pattern "palabra" -Recurse
```

## Solución de Problemas

### Error: "mux: command not found"
```bash
# Verificar instalación
pip list | grep mux-lang

# Reinstalar
pip uninstall mux-lang
pip install -e .
```

### Error al Importar Módulos
```bash
# Verificar que stdlib existe
ls mux_lang/stdlib/

# Reinstalar
pip install -e . --force-reinstall
```

### Error de Permisos
```bash
# Linux/macOS
sudo pip install -e .

# O usar usuario local
pip install -e . --user
```

---

**Creado por MushhX** 🌍⚙️
