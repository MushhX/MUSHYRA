# Guía del Ejecutable de Mux
**Creador: MushhX**

Esta guía explica cómo compilar y usar el ejecutable de Mux.

## 🔨 Compilar a Ejecutable

### Requisitos

- Python 3.8 o superior
- PyInstaller instalado

### Pasos para Compilar

1. **Instalar PyInstaller**
```bash
pip install pyinstaller
```

2. **Ejecutar script de compilación**
```bash
python build_exe.py
```

3. **Resultado**
El ejecutable se creará en la carpeta `dist/`:
- **Windows**: `dist/mux.exe`
- **Linux/macOS**: `dist/mux`

### Proceso de Compilación

El script `build_exe.py` realiza las siguientes acciones:

1. Crea un archivo temporal `mux_main.py`
2. Ejecuta PyInstaller con las siguientes opciones:
   - `--onefile`: Crea un único ejecutable
   - `--name=mux`: Nombre del ejecutable
   - `--clean`: Limpia archivos temporales
   - `--add-data`: Incluye la librería estándar
3. Limpia archivos temporales
4. Muestra mensaje de éxito

### Tamaño del Ejecutable

El ejecutable de Mux tiene aproximadamente:
- **Windows**: ~15-20 MB
- **Linux**: ~12-15 MB
- **macOS**: ~12-15 MB

## 🚀 Usar el Ejecutable

### Comandos Básicos

```bash
# Ver versión
mux.exe --version

# Ver ayuda
mux.exe --help

# Ejecutar programa
mux.exe archivo.mux
```

### Ejemplos de Uso

```bash
# Hola Mundo
mux.exe examples\hola_mundo.mux

# Calculadora
mux.exe examples\calculadora.mux

# Fibonacci
mux.exe examples\fibonacci.mux

# Comandos únicos
mux.exe examples\comandos_unicos.mux

# Usando paquetes
mux.exe examples\usando_paquetes.mux

# Listas y diccionarios
mux.exe examples\listas_y_diccionarios.mux
```

### Rutas Relativas y Absolutas

```bash
# Ruta relativa
mux.exe ejemplos\mi_programa.mux

# Ruta absoluta
mux.exe C:\Proyectos\MiApp\programa.mux

# Desde otro directorio
cd C:\Proyectos
mux.exe D:\Mux\examples\hola_mundo.mux
```

## 📦 Distribuir el Ejecutable

### Opción 1: Solo el Ejecutable

Puedes distribuir solo el archivo `mux.exe`. Los usuarios pueden ejecutar programas Mux sin instalar Python.

```
mi_proyecto/
├── mux.exe
├── mi_programa.mux
└── README.txt
```

### Opción 2: Con Librería Estándar

Si tus programas usan módulos de la librería estándar, incluye la carpeta `mux_lang/stdlib/`:

```
mi_proyecto/
├── mux.exe
├── mux_lang/
│   └── stdlib/
│       ├── math.mux
│       ├── time.mux
│       └── ...
├── mi_programa.mux
└── README.txt
```

### Opción 3: Instalador

Puedes crear un instalador usando herramientas como:
- **Windows**: Inno Setup, NSIS
- **Linux**: .deb, .rpm
- **macOS**: .dmg, .pkg

## 🔧 Solución de Problemas

### Error: "No se puede encontrar el módulo"

Si el ejecutable no encuentra módulos de la librería estándar:

1. Verifica que la carpeta `mux_lang/stdlib/` esté en el mismo directorio que el ejecutable
2. O recompila con:
```bash
python build_exe.py
```

### Error: "Archivo no encontrado"

Asegúrate de usar la ruta correcta al archivo .mux:

```bash
# Incorrecto
mux.exe hola_mundo.mux  # Si no está en el directorio actual

# Correcto
mux.exe examples\hola_mundo.mux
```

### El Ejecutable es Muy Grande

El tamaño del ejecutable incluye:
- Python runtime
- Librerías necesarias
- Librería estándar de Mux

Para reducir el tamaño:
1. Usa `--exclude-module` en PyInstaller para módulos no usados
2. Comprime el ejecutable con UPX
3. Distribuye solo las librerías necesarias

### Error en Windows Defender

Windows Defender puede marcar el ejecutable como sospechoso. Esto es normal para ejecutables creados con PyInstaller.

Soluciones:
1. Añade una excepción en Windows Defender
2. Firma digitalmente el ejecutable
3. Distribuye el código fuente también

## 🎯 Casos de Uso

### 1. Herramienta de Línea de Comandos

```bash
# Crear herramienta CLI
mux.exe mi_herramienta.mux --opcion valor
```

### 2. Script de Automatización

```bash
# Ejecutar script de automatización
mux.exe automatizar_tareas.mux
```

### 3. Aplicación Standalone

```bash
# Distribuir aplicación completa
mi_app/
├── mux.exe
├── app.mux
├── config.json
└── data/
```

### 4. Bot

```bash
# Ejecutar bot
mux.exe bot_discord.mux
```

## 📊 Comparación: Python vs Ejecutable

| Aspecto | Python | Ejecutable |
|---------|--------|------------|
| Requiere Python | ✅ Sí | ❌ No |
| Tamaño | ~10 KB | ~15-20 MB |
| Velocidad inicio | Rápido | Medio |
| Distribución | Compleja | Simple |
| Actualización | Fácil | Recompilar |

## 🚀 Optimizaciones

### Compilación Optimizada

```bash
# Con optimizaciones
pyinstaller --onefile --optimize=2 --name=mux mux_main.py
```

### Comprimir con UPX

```bash
# Instalar UPX
# Windows: Descargar de https://upx.github.io/

# Comprimir ejecutable
upx --best mux.exe
```

### Excluir Módulos No Usados

```bash
pyinstaller --onefile \
  --exclude-module tkinter \
  --exclude-module matplotlib \
  --name=mux mux_main.py
```

## 📝 Notas Importantes

1. **Compatibilidad**: El ejecutable solo funciona en el sistema operativo donde fue compilado
2. **Actualizaciones**: Debes recompilar para cada actualización
3. **Debugging**: Es más difícil debuggear ejecutables
4. **Antivirus**: Algunos antivirus pueden marcar falsos positivos

## 🎓 Mejores Prácticas

1. **Versiona tus ejecutables**: `mux-v1.0.0.exe`
2. **Incluye README**: Documenta cómo usar el ejecutable
3. **Prueba en sistemas limpios**: Sin Python instalado
4. **Firma digitalmente**: Para distribución profesional
5. **Incluye licencia**: LICENSE.txt junto al ejecutable

## 🔗 Recursos

- [PyInstaller Docs](https://pyinstaller.org/)
- [UPX](https://upx.github.io/)
- [Inno Setup](https://jrsoftware.org/isinfo.php)
- [NSIS](https://nsis.sourceforge.io/)

---

**Creado por MushhX** 🌍⚙️
