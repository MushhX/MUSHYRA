# Resumen de MUSHYRA

MUSHYRA es un lenguaje interpretado implementado en Python. El paquete declara la versión en `mux_lang/_version.py` y ofrece los comandos `myr` y `myr-pkg`; `mux` y `mux-pkg` se mantienen como alias.

## Componentes

- `lexer.py`: tokens, escapes de strings, normalización de saltos y ubicaciones.
- `parser.py`, `ast_nodes.py`: parser recursivo, nodos AST compatibles con tuplas, spans y validación estructural.
- `interpreter.py`: scopes léxicos, funciones, colecciones, módulos, errores contextualizados, presupuestos de pasos y límites de ejecución.
- `native_stdlib.py`: APIs estándar y puentes opcionales a servicios Python.
- `cli.py`, `formatter.py`, `linter.py`: ejecución, stdin, REPL, configuración, lint, formato, watch, tokens y AST.
- `package_manager.py`: instalaciones transaccionales, HTTPS, SHA-256, firmas Ed25519, índice configurable, lockfiles y auditoría.
- `examples/`: programas del lenguaje.

## Arquitectura

El lexer crea tokens con línea y columna. El parser conserva los saltos de línea que separan declaraciones y produce el AST consumido por el intérprete. Los módulos MUSHYRA locales y los paquetes del usuario se cargan desde archivos `.myr`; los módulos estándar son implementaciones nativas.

El runtime permite inyectar streams, limitar pasos/recursión y cancelar cooperativamente. `--sandbox-root` limita rutas de archivos y bloquea SQLite file escapes, pero no es una frontera para ejecutar código hostil.

## Instalación y uso

```console
python -m pip install .
myr examples/hola_mundo.myr
myr --check examples/hola_mundo.myr
```

Consulta [README.md](README.md), [INSTALL.md](INSTALL.md) y [STDLIB_REFERENCE.md](STDLIB_REFERENCE.md).
