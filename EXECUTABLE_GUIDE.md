# Crear y usar el ejecutable

## Compilar

La compilación se hace en la plataforma donde se ejecuta PyInstaller; no es un cross-compiler.

```console
python -m pip install ".[build]"
python build_exe.py
```

El binario aparece en `dist/`: `myr.exe` en Windows y `myr` en macOS/Linux. El tamaño depende del sistema y de las dependencias incluidas.

Para empaquetar una integración opcional, instala su extra antes de compilar. Por ejemplo:

```console
python -m pip install ".[build,web,discord]"
python build_exe.py
```

## Ejecutar

```console
dist/myr --version
dist/myr examples/hola_mundo.myr
dist/myr --check mi_programa.myr
```

En Windows, usa `dist\myr.exe` y separadores `\` para las rutas si lo prefieres. El CLI también admite `--tokens`, `--ast`, `--repl` y `--max-steps N`.

## Distribuir

Puedes distribuir el ejecutable con el archivo MUSHYRA, los datos que necesite y sus licencias. Las dependencias opcionales solo estarán disponibles si se instalaron en el entorno de compilación y PyInstaller las incluyó. Mantén los tokens y contraseñas fuera del binario y configúralos mediante variables de entorno en el sistema de destino.

Para generar un ZIP portable ejecuta `python create_portable_installer.py`. En Windows, `python build_installer.py` genera un instalador si Inno Setup 6 está disponible. Consulta [INSTALLER_GUIDE.md](INSTALLER_GUIDE.md).
