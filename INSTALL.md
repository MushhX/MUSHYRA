# Guía de Instalación de Mux
**Creador: MushhX**

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación Básica

### 1. Clonar o descargar el repositorio

```bash
git clone https://github.com/MushhX/Mux.git
cd mux
```

### 2. Instalar Mux

```bash
pip install -e .
```

Esto instalará Mux en modo desarrollo, permitiéndote usar los comandos `mux` y `mux-pkg` desde cualquier lugar.

### 3. Verificar instalación

```bash
mux --version
```

Deberías ver: `Mux v1.0.0`

## Instalación con Características Adicionales

### Para desarrollo web:
```bash
pip install -e ".[web]"
```

### Para bots de Discord:
```bash
pip install -e ".[discord]"
```

### Para bots de Telegram:
```bash
pip install -e ".[telegram]"
```

### Para WhatsApp (Twilio):
```bash
pip install -e ".[whatsapp]"
```

### Instalación completa (todas las características):
```bash
pip install -e ".[full]"
```

## Compilar a Ejecutable

Si quieres crear un ejecutable independiente (.exe en Windows):

### 1. Instalar PyInstaller

```bash
pip install pyinstaller
```

### 2. Ejecutar script de compilación

```bash
python build_exe.py
```

### 3. Usar el ejecutable

El ejecutable se creará en la carpeta `dist/`:

**Windows:**
```bash
dist\mux.exe examples\hola_mundo.mux
```

**Linux/macOS:**
```bash
./dist/mux examples/hola_mundo.mux
```

## Uso sin Instalación

Si no quieres instalar Mux, puedes ejecutarlo directamente:

```bash
python -m mux_lang.cli archivo.mux
```

## Probar la Instalación

Ejecuta algunos ejemplos para verificar que todo funciona:

```bash
mux examples/hola_mundo.mux
mux examples/calculadora.mux
mux examples/fibonacci.mux
mux examples/listas_y_diccionarios.mux
```

## Solución de Problemas

### Error: "mux: command not found"

Si después de instalar no puedes usar el comando `mux`, asegúrate de que el directorio de scripts de Python esté en tu PATH:

**Windows:**
```bash
# Añadir a PATH: C:\Users\TuUsuario\AppData\Local\Programs\Python\Python3X\Scripts
```

**Linux/macOS:**
```bash
export PATH="$HOME/.local/bin:$PATH"
# Añade esta línea a tu ~/.bashrc o ~/.zshrc
```

### Error al importar módulos

Si tienes problemas al importar módulos de la librería estándar, verifica que la carpeta `mux_lang/stdlib/` existe y contiene los archivos `.mux`.

### Error con PyInstaller

Si la compilación falla, asegúrate de tener la última versión:

```bash
pip install --upgrade pyinstaller
```

## Desinstalación

Para desinstalar Mux:

```bash
pip uninstall mux-lang
```

## Soporte

Si tienes problemas con la instalación, abre un issue en el repositorio de GitHub.

---

**Creado por MushhX** 🌍⚙️
