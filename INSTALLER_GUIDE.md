# Guía del instalador Windows

El instalador disponible se genera con Inno Setup 6 en Windows x64. Los nombres y tamaños finales dependen de la versión y plataforma de compilación.

## Requisitos

- Python 3.8 o posterior de 64 bits.
- Inno Setup 6, con `ISCC.exe` disponible en PATH o en su carpeta habitual.
- Pillow y PyInstaller, instalables con `python -m pip install ".[build]"`.

## Crear el instalador

Desde la raíz del repositorio:

```console
python build_exe.py
python build_installer.py
```

El primer comando crea `dist/myr.exe`. El segundo prepara el icono si falta, sustituye las rutas y versión en `installer.iss` y crea `installer_output/mushyra-setup-<versión>.exe`.

## Contenido y opciones

El instalador incluye el ejecutable, ejemplos y la documentación seleccionada en `installer.iss`. Se instala en el perfil del usuario, crea accesos directos y ofrece agregar la carpeta de instalación al PATH. Los módulos nativos forman parte del paquete Python compilado; no hay una carpeta externa `stdlib` que copiar.

Las integraciones opcionales se incorporan al ejecutable solo si sus dependencias están instaladas en el entorno usado para compilar. Los secretos de bots y correo deben configurarse en el equipo donde se ejecutará el programa.

## Crear un ZIP portable

```console
python create_portable_installer.py
```

El ZIP queda en la raíz del repositorio de forma predeterminada. Usa `--output-dir RUTA` para guardar en otra carpeta. Incluye `SHA256SUMS.txt` para verificar los archivos empaquetados.

Este repositorio no genera MSI, instaladores Linux/macOS ni firmas digitales. Para distribuir una release, publica el hash del artefacto junto a la versión y conserva el entorno y los registros de compilación.
