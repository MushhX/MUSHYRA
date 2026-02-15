# Descargar Mux v1.0.0
**Creador: MushhX**

## 📦 Opciones de Descarga

### 1. Instalador Portable (Recomendado) ✅

**Archivo**: `mux-portable-v1.0.0-windows-x64.zip`  
**Tamaño**: 7.75 MB  
**Plataforma**: Windows x64  
**Requiere Python**: ❌ NO

**Contenido:**
- Ejecutable de Mux (7.89 MB)
- Librería estándar (15 módulos)
- Ejemplos (20+ archivos)
- Documentación completa

**Instalación:**
1. Descarga el archivo ZIP
2. Extrae en cualquier carpeta
3. Lee `INSTALL.txt` para instrucciones
4. Ejecuta: `mux.exe examples\hola_mundo.mux`

**Descarga**: [mux-portable-v1.0.0-windows-x64.zip](mux-portable-v1.0.0-windows-x64.zip)

---

### 2. Ejecutable Standalone ✅

**Archivo**: `mux.exe`  
**Tamaño**: 7.89 MB  
**Plataforma**: Windows x64  
**Requiere Python**: ❌ NO

**Uso:**
```bash
mux.exe programa.mux
```

**Descarga**: [dist/mux.exe](dist/mux.exe)

---

### 3. Código Fuente ✅

**Repositorio**: GitHub  
**Requiere Python**: ✅ SÍ (3.8+)

**Instalación:**
```bash
git clone https://github.com/mushhx/mux.git
cd mux
pip install -e .
mux programa.mux
```

**Descarga**: [GitHub Repository](https://github.com/mushhx/mux)

---

### 4. Instalador Inno Setup ⚠️

**Archivo**: `mux-setup-1.0.0.exe`  
**Tamaño**: ~8 MB  
**Plataforma**: Windows x64  
**Estado**: Requiere Inno Setup para crear

**Características:**
- Instalación en Program Files
- Opción de agregar al PATH
- Accesos directos automáticos
- Desinstalador incluido

**Cómo crear:**
1. Instala [Inno Setup](https://jrsoftware.org/isdl.php)
2. Ejecuta: `python build_installer.py`

---

## 🚀 Inicio Rápido

### Opción 1: Instalador Portable

```bash
# 1. Descarga y extrae
# 2. Abre terminal en la carpeta extraída
# 3. Ejecuta un ejemplo
mux.exe examples\hola_mundo.mux
```

### Opción 2: Desde Código Fuente

```bash
# 1. Clona el repositorio
git clone https://github.com/mushhx/mux.git
cd mux

# 2. Instala
pip install -e .

# 3. Ejecuta un ejemplo
mux examples/hola_mundo.mux
```

## 📋 Requisitos del Sistema

### Para Ejecutable/Instalador Portable
- **Sistema Operativo**: Windows 7/8/10/11 (x64)
- **RAM**: 100 MB mínimo
- **Espacio en disco**: 50 MB
- **Python**: ❌ NO requerido

### Para Código Fuente
- **Sistema Operativo**: Windows/Linux/macOS
- **Python**: 3.8 o superior
- **pip**: Gestor de paquetes de Python
- **Espacio en disco**: 20 MB

## 🔍 Verificar Descarga

### Tamaños de Archivo

```
mux-portable-v1.0.0-windows-x64.zip: 7.75 MB
mux.exe: 7.89 MB
```

### Checksums (SHA256)

```bash
# Verificar integridad del archivo
certutil -hashfile mux-portable-v1.0.0-windows-x64.zip SHA256
```

## 🛡️ Seguridad

### Antivirus

Los ejecutables creados con PyInstaller pueden ser marcados como falsos positivos por algunos antivirus. Esto es normal y seguro.

**Si tu antivirus bloquea el archivo:**
1. Añade una excepción para Mux
2. O descarga el código fuente y compila tú mismo

### Código Abierto

Mux es 100% código abierto. Puedes revisar todo el código en GitHub antes de ejecutarlo.

## 📦 Contenido de las Descargas

### Instalador Portable (ZIP)
```
mux/
├── mux.exe (7.89 MB)
├── mux_lang/
│   └── stdlib/ (15 módulos)
├── examples/ (20+ archivos)
├── README.md
├── QUICKSTART.md
├── FEATURES.md
├── STDLIB_REFERENCE.md
├── UNIQUE_COMMANDS.md
├── EXECUTABLE_GUIDE.md
├── INSTALL.txt
├── VERSION.txt
└── LICENSE
```

### Código Fuente
```
mux/
├── mux_lang/ (código fuente)
├── examples/ (ejemplos)
├── docs/ (documentación)
├── setup.py
├── build_exe.py
└── ...
```

## 🆘 Soporte

### Problemas con la Descarga
- Verifica tu conexión a internet
- Intenta descargar desde otro navegador
- Contacta en GitHub Issues

### Problemas con la Instalación
- Lee [INSTALL.md](INSTALL.md)
- Lee [EXECUTABLE_GUIDE.md](EXECUTABLE_GUIDE.md)
- Abre un issue en GitHub

### Preguntas
- Lee [QUICKSTART.md](QUICKSTART.md)
- Lee [README.md](README.md)
- Pregunta en GitHub Issues

## 🔗 Enlaces

- **Repositorio**: https://github.com/mushhx/mux
- **Documentación**: Ver archivos .md
- **Issues**: https://github.com/mushhx/mux/issues
- **Releases**: https://github.com/mushhx/mux/releases

## 📝 Licencia

Mux está licenciado bajo MIT License. Ver [LICENSE](LICENSE) para más detalles.

## 🙏 Agradecimientos

Gracias por descargar Mux. ¡Esperamos que disfrutes programando con él!

---

**Mux: Una pequeña nación digital** 🌍⚙️

**Creado con ❤️ por MushhX**
