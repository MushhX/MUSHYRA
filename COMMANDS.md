# Comandos útiles

## Instalar y ejecutar

```console
python -m pip install .
myr init mi-proyecto
myr --version
myr mi-proyecto/main.myr
myr examples/hola_mundo.myr
```

## CLI

```console
myr --help
myr --check programa.myr
myr --lint programa.myr
myr --diagnostics-format json programa.myr
myr --format programa.myr
myr --write-format programa.myr
myr --watch programa.myr
myr --tokens programa.myr
myr --ast programa.myr
myr --max-steps 10000 programa.myr
myr --max-call-depth 96 programa.myr
myr --max-output-bytes 1048576 programa.myr
myr --timeout-seconds 15 programa.myr
myr --sandbox --sandbox-root ./proyecto programa.myr
myr --debugger programa.myr
myr --lsp
myr --time benchmarks/interpreter_suite.myr
myr programa.myr -- valor
myr --debug programa.myr
myr --repl
myr -
myr init tienda --template app
myr init saludos --template library
```

El depurador empieza detenido en la primera declaración. Usa `step`, `continue`, `break <línea> [if <expresión MUSHYRA>]`, `watch <expresión>`, `unwatch <número>`, `vars`, `scopes`, `modules`, `bt` y `quit` en el prompt `myr-debug>`. Las condiciones y observaciones se evalúan con el estado actual del intérprete. `--debug` muestra tracebacks internos; `--debugger` controla la ejecución MUSHYRA.

`myr --lsp` inicia el servidor de lenguaje por stdin/stdout para editores. La extensión de VS Code en `editors/vscode` lo usa para diagnósticos, autocompletado, ir a definición, referencias y símbolos del documento.

`myr -` lee el fuente desde stdin. En PowerShell, por ejemplo, `Get-Content programa.myr -Raw | myr -`.

## Gestor de paquetes

```console
myr-pkg list
myr-pkg list --json
myr-pkg install ./paquete --name saludos
myr-pkg install ./main.myr --name saludos
myr-pkg install https://example.org/saludos.zip --name saludos --sha256 HASH
myr-pkg search saludo --registry https://example.org/index.json --trust-store claves.json
myr-pkg install saludos --from-registry --registry https://example.org/index.json --trust-store claves.json
myr-pkg lock
myr-pkg install-lock
myr-pkg verify
myr-pkg audit
myr-pkg outdated --registry https://example.org/index.json --trust-store claves.json
myr-pkg hashes ./saludos
myr-pkg remove saludos
```

Las descargas HTTPS requieren hash SHA-256; las instalaciones remotas normales también requieren firma Ed25519 y una clave pública confiable. El registro se configura con `MYR_PACKAGE_REGISTRY` o `--registry`; el proyecto no mantiene un servicio público.

## Extras opcionales

```console
python -m pip install ".[web]"
python -m pip install ".[discord]"
python -m pip install ".[telegram]"
python -m pip install ".[whatsapp]"
python -m pip install ".[crypto]"
```

## Autocompletado del shell

Carga `editors/completions/myr.bash` desde tu perfil de Bash o ejecuta `. editors/completions/myr.ps1` desde tu perfil de PowerShell para completar opciones y rutas.

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
