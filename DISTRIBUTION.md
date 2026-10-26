# Distribuir Mux

Este repositorio contiene scripts para crear artefactos localmente, pero no versiona binarios precompilados. El resultado depende del sistema y del entorno que ejecute la compilación.

## Instalar desde el código fuente

```console
python -m pip install .
```

## Construir un ejecutable

```console
python -m pip install ".[build]"
python build_exe.py
```

`build_exe.py` ejecuta PyInstaller en modo `onefile` para la plataforma actual y deja el resultado en `dist/`. Para incluir una integración opcional dentro del ejecutable, instala su extra antes de compilar, por ejemplo `python -m pip install ".[web,discord]"`.

## ZIP portable

Después de crear el ejecutable:

```console
python create_portable_installer.py
```

El ZIP contiene el binario, ejemplos, documentación, versión y un archivo `SHA256SUMS.txt`. Para elegir otra carpeta usa `--output-dir RUTA`.

## Instalador Windows

En Windows x64, instala Inno Setup 6 y las dependencias de build, compila `dist/mux.exe` y ejecuta:

```console
python build_installer.py
```

El resultado queda en `installer_output/`. El instalador añade accesos directos opcionales y puede agregar Mux al PATH del usuario. No se crea MSI ni paquete Linux/macOS con los scripts actuales.

## Publicación de paquetes Python

Antes de publicar en PyPI, revisa `setup.py`, `pyproject.toml`, `LICENSE`, la versión y las notas de versión. Instala `build` y `twine`, construye y revisa los artefactos localmente con `python -m build` y `twine check dist/*`. Publicar requiere una cuenta y credenciales de PyPI, y debe hacerse como paso explícito de release.
