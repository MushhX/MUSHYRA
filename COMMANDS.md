# Comandos útiles

## Instalar y ejecutar

```console
python -m pip install .
mux init mi-proyecto
mux --version
mux mi-proyecto/main.mux
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
mux --max-output-bytes 1048576 programa.mux
mux --timeout-seconds 15 programa.mux
mux --sandbox --sandbox-root ./proyecto programa.mux
mux --debugger programa.mux
mux --lsp
mux --time benchmarks/interpreter_suite.mux
mux programa.mux -- valor
mux --debug programa.mux
mux --repl
mux -
```

El depurador empieza detenido en la primera declaración. Usa `step`, `continue`, `break <línea>`, `vars`, `bt` y `quit` en el prompt `mux-debug>`. `--debug` sigue mostrando tracebacks internos; `--debugger` controla la ejecución Mux.

`mux --lsp` inicia el servidor de lenguaje por stdin/stdout para editores. La extensión de VS Code en `editors/vscode` lo usa para diagnósticos, autocompletado, ir a definición, referencias y símbolos del documento.

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

## Autocompletado del shell

Carga `editors/completions/mux.bash` desde tu perfil de Bash o ejecuta `. editors/completions/mux.ps1` desde tu perfil de PowerShell para completar opciones y rutas.

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
