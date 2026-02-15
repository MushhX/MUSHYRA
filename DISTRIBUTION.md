# Guía de Distribución de Mux
**Creador: MushhX**

Esta guía explica cómo distribuir Mux de diferentes formas.

## 📦 Opciones de Distribución

### 1. Código Fuente (GitHub)

La forma más común de distribuir proyectos open source.

```bash
# Clonar repositorio
git clone https://github.com/mushhx/mux.git
cd mux
pip install -e .
```

**Ventajas:**
- Fácil de actualizar
- Transparente
- Permite contribuciones

**Desventajas:**
- Requiere Python
- Requiere Git

### 2. PyPI (Python Package Index)

Distribuir como paquete Python oficial.

```bash
# Instalar desde PyPI
pip install mux-lang
```

**Pasos para publicar:**

```bash
# 1. Instalar herramientas
pip install build twine

# 2. Crear distribución
python -m build

# 3. Subir a PyPI (test)
twine upload --repository testpypi dist/*

# 4. Subir a PyPI (producción)
twine upload dist/*
```

**Ventajas:**
- Instalación estándar
- Gestión de versiones
- Dependencias automáticas

**Desventajas:**
- Requiere Python
- Proceso de publicación

### 3. Ejecutable Standalone

Distribuir el ejecutable compilado.

**Windows:**
```
mux-v1.0.0-windows.zip
├── mux.exe (7.89 MB)
├── README.txt
└── LICENSE.txt
```

**Linux:**
```
mux-v1.0.0-linux.tar.gz
├── mux
├── README.txt
└── LICENSE.txt
```

**macOS:**
```
mux-v1.0.0-macos.dmg
├── mux
├── README.txt
└── LICENSE.txt
```

**Ventajas:**
- No requiere Python
- Fácil de usar
- Portable

**Desventajas:**
- Tamaño mayor
- Un ejecutable por OS
- Más difícil de actualizar

### 4. Instalador

Crear instaladores nativos para cada plataforma.

**Windows (Inno Setup):**
```bash
# Crear instalador .exe
iscc mux-installer.iss
```

**Linux (DEB/RPM):**
```bash
# Crear paquete .deb
dpkg-deb --build mux-1.0.0

# Crear paquete .rpm
rpmbuild -ba mux.spec
```

**macOS (DMG):**
```bash
# Crear imagen .dmg
hdiutil create -volname "Mux" -srcfolder dist -ov -format UDZO mux-1.0.0.dmg
```

**Ventajas:**
- Instalación profesional
- Integración con sistema
- Desinstalación fácil

**Desventajas:**
- Más complejo
- Requiere herramientas específicas

### 5. Docker

Distribuir como contenedor Docker.

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

ENTRYPOINT ["mux"]
```

```bash
# Construir imagen
docker build -t mux:1.0.0 .

# Ejecutar
docker run -v $(pwd):/workspace mux:1.0.0 /workspace/programa.mux
```

**Ventajas:**
- Entorno consistente
- Fácil de desplegar
- Aislamiento

**Desventajas:**
- Requiere Docker
- Overhead de contenedor

## 📋 Checklist de Distribución

### Antes de Distribuir

- [ ] Todos los tests pasan
- [ ] Documentación actualizada
- [ ] Versión actualizada en `setup.py`
- [ ] CHANGELOG.md actualizado
- [ ] README.md actualizado
- [ ] Ejemplos funcionan
- [ ] Licencia incluida

### Para Código Fuente

- [ ] Repositorio limpio (sin archivos temporales)
- [ ] .gitignore configurado
- [ ] README con instrucciones claras
- [ ] requirements.txt actualizado
- [ ] setup.py configurado

### Para Ejecutable

- [ ] Compilado en sistema limpio
- [ ] Probado sin Python instalado
- [ ] Incluye README.txt
- [ ] Incluye LICENSE.txt
- [ ] Firmado digitalmente (opcional)

### Para PyPI

- [ ] setup.py completo
- [ ] README.md en formato correcto
- [ ] Versión única (no repetida)
- [ ] Dependencias especificadas
- [ ] Clasificadores correctos

## 🔐 Firma Digital

### Windows (SignTool)

```bash
signtool sign /f certificado.pfx /p password /t http://timestamp.digicert.com mux.exe
```

### macOS (codesign)

```bash
codesign --sign "Developer ID" --timestamp mux
```

### Linux (GPG)

```bash
gpg --detach-sign --armor mux
```

## 📝 Archivos de Distribución

### README.txt (para ejecutable)

```
Mux Programming Language v1.0.0
Creador: MushhX

INSTALACIÓN:
No requiere instalación. Simplemente ejecuta:
  mux.exe programa.mux

EJEMPLOS:
Ver carpeta examples/ para ejemplos de código.

DOCUMENTACIÓN:
https://github.com/mushhx/mux

LICENCIA:
MIT License - Ver LICENSE.txt

SOPORTE:
https://github.com/mushhx/mux/issues
```

### VERSION.txt

```
Mux v1.0.0
Build: 2026-02-15
Platform: Windows x64
Python: 3.12
```

## 🌐 Plataformas de Distribución

### GitHub Releases

1. Crear tag de versión
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

2. Crear release en GitHub
3. Subir ejecutables como assets

### SourceForge

Alternativa a GitHub para distribución de binarios.

### Microsoft Store (Windows)

Para distribución profesional en Windows.

### Snap Store (Linux)

```bash
snapcraft
snapcraft upload mux_1.0.0_amd64.snap
```

### Homebrew (macOS)

Crear formula para Homebrew:

```ruby
class Mux < Formula
  desc "Lenguaje de programación moderno y accesible"
  homepage "https://github.com/mushhx/mux"
  url "https://github.com/mushhx/mux/archive/v1.0.0.tar.gz"
  sha256 "..."

  depends_on "python@3.11"

  def install
    system "pip3", "install", "-e", "."
  end
end
```

## 📊 Métricas de Distribución

### Seguimiento

- Descargas de GitHub Releases
- Instalaciones desde PyPI
- Clones del repositorio
- Stars en GitHub
- Issues y Pull Requests

### Herramientas

- GitHub Insights
- PyPI Stats
- Google Analytics (para sitio web)

## 🔄 Actualizaciones

### Versionado Semántico

```
MAJOR.MINOR.PATCH
1.0.0

MAJOR: Cambios incompatibles
MINOR: Nuevas características compatibles
PATCH: Correcciones de bugs
```

### Proceso de Actualización

1. Actualizar código
2. Actualizar versión en `setup.py`
3. Actualizar CHANGELOG.md
4. Crear tag de versión
5. Compilar ejecutables
6. Publicar en PyPI
7. Crear GitHub Release
8. Anunciar actualización

## 📢 Promoción

### Canales

- GitHub README
- PyPI descripción
- Reddit (r/programming, r/learnprogramming)
- Hacker News
- Twitter/X
- Dev.to
- Medium
- YouTube (tutoriales)

### Contenido

- Artículos de blog
- Tutoriales en video
- Ejemplos de código
- Comparaciones con otros lenguajes
- Casos de uso reales

## 🎯 Público Objetivo

1. **Principiantes**: Aprender programación
2. **Educadores**: Enseñar programación
3. **Scripters**: Automatización rápida
4. **Desarrolladores**: Prototipado rápido
5. **Makers**: Proyectos personales

## 📝 Licencia

Mux usa licencia MIT, que permite:
- Uso comercial
- Modificación
- Distribución
- Uso privado

Con las condiciones:
- Incluir licencia y copyright
- Sin garantía

---

**Creado por MushhX** 🌍⚙️
