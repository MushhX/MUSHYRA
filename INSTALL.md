# Instalar Mux

Mux requiere Python 3.8 o posterior.

## Desde el repositorio

```console
git clone https://github.com/MushhX/Mux.git
cd Mux
python -m pip install .
mux --version
mux examples/hola_mundo.mux
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
```

También puedes combinar extras, por ejemplo `python -m pip install ".[web,telegram]"`. La integración de correo usa la biblioteca SMTP incluida con Python; SQLite también está incluido.

## Ejecutar sin instalar

Desde la raíz del repositorio:

```console
python -m mux_lang examples/hola_mundo.mux
```

## Crear un ejecutable

```console
python -m pip install ".[build]"
python build_exe.py
```

El artefacto aparece en `dist/` y se construye para la plataforma actual. En Windows, instala Inno Setup 6 y ejecuta `python build_installer.py` para crear el instalador. `python create_portable_installer.py` crea un ZIP portable.

## Solución de problemas

- Si `mux` no aparece, confirma que el directorio de scripts de Python está en `PATH`, o ejecuta `python -m mux_lang.cli archivo.mux`.
- Los errores del lenguaje incluyen archivo, línea y columna. `mux --debug archivo.mux` muestra el traceback de la causa interna.
- Si falta una integración, instala su extra correspondiente. Los módulos locales y los paquetes instalados con `mux-pkg` se resuelven desde el directorio del programa y el directorio de datos Mux.
- Define `MUX_HOME` para cambiar el directorio del gestor de paquetes.

## Desinstalar

```console
python -m pip uninstall mux-lang
```

Esto no elimina paquetes Mux guardados en el directorio de datos del usuario.
