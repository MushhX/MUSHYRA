# Comandos útiles

## Instalar y ejecutar

```console
python -m pip install .
mux --version
mux examples/hola_mundo.mux
python -m mux_lang.cli examples/hola_mundo.mux
```

## CLI

```console
mux --help
mux --check programa.mux
mux --tokens programa.mux
mux --ast programa.mux
mux --max-steps 10000 programa.mux
mux --debug programa.mux
mux --repl
mux -
```

`mux -` lee el fuente desde stdin. En PowerShell, por ejemplo, `Get-Content programa.mux -Raw | mux -`.

## Gestor de paquetes

```console
mux-pkg list
mux-pkg list --json
mux-pkg install ./paquete --name saludos
mux-pkg install ./main.mux --name saludos
mux-pkg install https://example.org/saludos.zip --name saludos --sha256 HASH
mux-pkg remove saludos
```

El origen HTTPS debe ser un ZIP y requiere su hash SHA-256. No se consulta un catálogo remoto.

## Extras opcionales

```console
python -m pip install ".[web]"
python -m pip install ".[discord]"
python -m pip install ".[telegram]"
python -m pip install ".[whatsapp]"
python -m pip install ".[crypto]"
```

## Empaquetar

```console
python -m pip install ".[build]"
python build_exe.py
python create_portable_installer.py
python create_portable_installer.py --output-dir ./artifacts
python build_installer.py  # Windows con Inno Setup 6
```

## Desarrollo

```console
python -m pip install -e .
git status --short
git diff
```
