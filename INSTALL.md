# Instalar MUSHYRA

MUSHYRA requiere Python 3.8 o posterior.

## Desde el repositorio

```console
git clone https://github.com/MushhX/MUSHYRA.git
cd MUSHYRA
python -m pip install .
myr --version
myr examples/hola_mundo.myr
```

Para desarrollar sobre el checkout usa `python -m pip install -e .`.

## Integraciones opcionales

Instala solo los extras que use tu programa:

```console
python -m pip install ".[web]"
python -m pip install ".[discord]"
python -m pip install ".[telegram]"
python -m pip install ".[whatsapp]"
python -m pip install ".[crypto]"
python -m pip install ".[regex]"
```

También puedes combinar extras, por ejemplo `python -m pip install ".[web,telegram]"`. La integración de correo usa la biblioteca SMTP incluida con Python; SQLite también está incluido.

## Ejecutar sin instalar

Desde la raíz del repositorio, invoca el ejecutable de consola:

```console
myr examples/hola_mundo.myr
```

## Crear un ejecutable

```console
python -m pip install ".[build]"
python build_exe.py
```

El artefacto aparece en `dist/` y se construye para la plataforma actual. En Windows, instala Inno Setup 6 y ejecuta `python build_installer.py` para crear el instalador. `python create_portable_installer.py` crea un ZIP portable.

## Solución de problemas

- Si `myr` no aparece, confirma que el directorio de scripts de Python está en `PATH` o instala el paquete de nuevo; los programas MUSHYRA se ejecutan con `myr archivo.myr`.
- Los errores del lenguaje incluyen archivo, línea y columna. `myr --debug archivo.myr` muestra el traceback de la causa interna.
- Si falta una integración, instala su extra correspondiente. Los módulos locales y los paquetes instalados con `myr-pkg` se resuelven desde el directorio del programa y el directorio de datos MUSHYRA.
- Define `MYR_HOME` para cambiar el directorio del gestor de paquetes.

## Desinstalar

```console
python -m pip uninstall mushyra
```

Esto no elimina paquetes MUSHYRA guardados en el directorio de datos del usuario.
