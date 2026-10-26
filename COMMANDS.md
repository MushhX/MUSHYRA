# Comandos útiles

## Instalar y ejecutar

```console
python -m pip install .
mux --version
mux examples/hola_mundo.mux
```

## CLI

```console
mux --help
mux --check programa.mux
mux --lint programa.mux
mux --diagnostics-format json programa.mux
mux --format programa.mux
mux --write-format programa.mux
mux --watch programa.mux
mux --tokens programa.mux
mux --ast programa.mux
mux --max-steps 10000 programa.mux
mux --max-call-depth 96 programa.mux
mux programa.mux -- valor
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
mux-pkg search saludo --registry https://example.org/index.json --trust-store claves.json
mux-pkg install saludos --from-registry --registry https://example.org/index.json --trust-store claves.json
mux-pkg lock
mux-pkg install-lock
mux-pkg verify
mux-pkg audit
mux-pkg outdated --registry https://example.org/index.json --trust-store claves.json
mux-pkg hashes ./saludos
mux-pkg remove saludos
```

Las descargas HTTPS requieren hash SHA-256; las instalaciones remotas normales también requieren firma Ed25519 y una clave pública confiable. El registro se configura con `MUX_PACKAGE_REGISTRY` o `--registry`; el proyecto no mantiene un servicio público.

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
