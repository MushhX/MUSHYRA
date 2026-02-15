# Guía de Instaladores de Mux
**Creador: MushhX**

Esta guía explica los diferentes tipos de instaladores disponibles para Mux.

## 📦 Tipos de Instaladores

### 1. Instalador Portable (ZIP) ✅ DISPONIBLE

El instalador más simple y universal.

**Archivo**: `mux-portable-v1.0.0-windows-x64.zip` (7.75 MB)

**Ventajas:**
- ✅ No requiere instalación
- ✅ No requiere permisos de administrador
- ✅ Portable (USB, carpeta compartida)
- ✅ Fácil de distribuir
- ✅ No deja rastros en el sistema

**Desventajas:**
- ❌ No se agrega automáticamente al PATH
- ❌ No crea accesos directos
- ❌ No tiene desinstalador

**Cómo crear:**
```bash
python create_portable_installer.py
```

**Cómo usar:**
1. Extrae el ZIP
2. Lee INSTALL.txt
3. Ejecuta: `mux.exe programa.mux`

---

### 2. Instalador Inno Setup (EXE) 🔧 REQUIERE INNO SETUP

Instalador profesional con interfaz gráfica.

**Archivo**: `mux-setup-1.0.0.exe` (~8 MB)

**Ventajas:**
- ✅ Interfaz gráfica profesional
- ✅ Instalación en Program Files
- ✅ Opción de agregar al PATH
- ✅ Accesos directos automáticos
- ✅ Desinstalador incluido
- ✅ Soporte multiidioma

**Desventajas:**
- ❌ Requiere Inno Setup para crear
- ❌ Requiere permisos de administrador (opcional)

**Cómo crear:**

1. **Instalar Inno Setup**
   - Descarga: https://jrsoftware.org/isdl.php
   - Instala Inno Setup 6

2. **Crear instalador**
   ```bash
   python build_installer.py
   ```
   
   O manualmente:
   - Abre `installer.iss` con Inno Setup
   - Click en "Compile"

**Características del instalador:**
- Instalación en `C:\Program Files\Mux`
- Opción de agregar al PATH del sistema
- Accesos directos en menú inicio
- Icono personalizado
- Desinstalador en Panel de Control
- Soporte para español e inglés

---

### 3. Instalador MSI (Windows Installer) 🔧 REQUIERE WIX

Instalador nativo de Windows.

**Archivo**: `mux-1.0.0.msi` (~8 MB)

**Ventajas:**
- ✅ Formato nativo de Windows
- ✅ Gestión centralizada (GPO)
- ✅ Reparación automática
- ✅ Rollback en caso de error

**Desventajas:**
- ❌ Requiere WiX Toolset para crear
- ❌ Más complejo de configurar

**Cómo crear:**

1. **Instalar WiX Toolset**
   - Descarga: https://wixtoolset.org/
   - Instala WiX Toolset 3.11+

2. **Crear instalador**
   ```bash
   python build_msi_installer.py
   ```

---

### 4. Instalador NSIS 🔧 REQUIERE NSIS

Alternativa a Inno Setup.

**Archivo**: `mux-setup-1.0.0.exe` (~8 MB)

**Ventajas:**
- ✅ Muy personalizable
- ✅ Plugins disponibles
- ✅ Compresión eficiente

**Desventajas:**
- ❌ Requiere NSIS para crear
- ❌ Sintaxis más compleja

---

## 🚀 Comparación de Instaladores

| Característica | Portable ZIP | Inno Setup | MSI | NSIS |
|---------------|--------------|------------|-----|------|
| Fácil de crear | ✅ | ⚠️ | ❌ | ⚠️ |
| Fácil de usar | ✅ | ✅ | ✅ | ✅ |
| Requiere admin | ❌ | ⚠️ | ✅ | ⚠️ |
| Desinstalador | ❌ | ✅ | ✅ | ✅ |
| PATH automático | ❌ | ✅ | ✅ | ✅ |
| Accesos directos | ❌ | ✅ | ✅ | ✅ |
| Portable | ✅ | ❌ | ❌ | ❌ |
| Tamaño | 7.75 MB | ~8 MB | ~8 MB | ~8 MB |

## 📋 Recomendaciones

### Para Usuarios Finales
**Recomendado**: Instalador Inno Setup (EXE)
- Instalación profesional
- Fácil de usar
- Desinstalación limpia

### Para Desarrolladores
**Recomendado**: Instalador Portable (ZIP)
- No requiere instalación
- Fácil de probar
- Portable

### Para Empresas
**Recomendado**: Instalador MSI
- Gestión centralizada
- Políticas de grupo
- Instalación silenciosa

### Para Distribución Rápida
**Recomendado**: Instalador Portable (ZIP)
- Más pequeño
- Sin dependencias
- Universal

## 🛠️ Crear Todos los Instaladores

```bash
# 1. Compilar ejecutable
python build_exe.py

# 2. Crear icono
python create_icon.py

# 3. Crear instalador portable (siempre funciona)
python create_portable_installer.py

# 4. Crear instalador Inno Setup (si está instalado)
python build_installer.py

# 5. Crear instalador MSI (si WiX está instalado)
python build_msi_installer.py
```

## 📦 Contenido de los Instaladores

Todos los instaladores incluyen:

- **Ejecutable**: mux.exe (7.89 MB)
- **Librería estándar**: 15 módulos
  - math, http, web, discord_bot, telegram_bot
  - strings, regex, random, database, filesystem
  - crypto, time, json, console, email
- **Ejemplos**: 20+ archivos .mux
- **Documentación**: 15 archivos .md
- **Licencia**: MIT License

## 🔐 Firma Digital

Para distribución profesional, firma los instaladores:

```bash
# Windows (SignTool)
signtool sign /f certificado.pfx /p password /t http://timestamp.digicert.com mux-setup-1.0.0.exe

# Verificar firma
signtool verify /pa mux-setup-1.0.0.exe
```

## 📊 Estadísticas de Instaladores

| Instalador | Tamaño | Tiempo Instalación | Tiempo Desinstalación |
|-----------|--------|-------------------|---------------------|
| Portable ZIP | 7.75 MB | 0s (extracción) | 0s (eliminar carpeta) |
| Inno Setup | ~8 MB | ~10s | ~5s |
| MSI | ~8 MB | ~15s | ~10s |
| NSIS | ~8 MB | ~10s | ~5s |

## 🎯 Casos de Uso

### Desarrollo y Testing
```bash
# Usar portable
python create_portable_installer.py
# Extraer y probar
```

### Distribución a Usuarios
```bash
# Crear instalador Inno Setup
python build_installer.py
# Distribuir mux-setup-1.0.0.exe
```

### Distribución Empresarial
```bash
# Crear MSI
python build_msi_installer.py
# Desplegar via GPO
```

### Distribución en USB
```bash
# Usar portable
python create_portable_installer.py
# Copiar a USB
```

## 📝 Notas Importantes

1. **Portable es suficiente**: Para la mayoría de usuarios, el instalador portable es suficiente
2. **Inno Setup es profesional**: Si quieres un instalador con interfaz gráfica
3. **MSI para empresas**: Solo si necesitas gestión centralizada
4. **Firma digital**: Recomendada para distribución pública

## 🔗 Enlaces Útiles

- **Inno Setup**: https://jrsoftware.org/
- **WiX Toolset**: https://wixtoolset.org/
- **NSIS**: https://nsis.sourceforge.io/
- **SignTool**: Incluido en Windows SDK

---

**Creado por MushhX** 🌍⚙️
