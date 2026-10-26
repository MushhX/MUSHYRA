# Resumen de Mux

Mux es un lenguaje interpretado implementado en Python. El paquete declara la versión en `mux_lang/_version.py` y ofrece dos comandos de consola: `mux` y `mux-pkg`.

## Componentes

- `lexer.py`: tokens, escapes de strings, normalización de saltos y ubicaciones.
- `parser.py`: parser recursivo, AST de tuplas y validación estructural.
- `interpreter.py`: scopes léxicos, funciones, colecciones, módulos, errores contextualizados y límite opcional de pasos.
- `native_stdlib.py`: APIs estándar y puentes opcionales a servicios Python.
- `cli.py`: ejecución, stdin, REPL, comprobación de sintaxis, tokens y AST.
- `package_manager.py`: instalación y eliminación transaccional de paquetes locales o ZIP HTTPS con SHA-256.
- `examples/`: programas del lenguaje.

## Arquitectura

El lexer crea tokens con línea y columna. El parser conserva los saltos de línea que separan declaraciones y produce el AST consumido por el intérprete. Los módulos Mux locales y los paquetes del usuario se cargan desde archivos `.mux`; los módulos estándar son implementaciones nativas.

El runtime permite inyectar streams y limita la ejecución si se define `max_steps`. No es un sandbox: un programa Mux puede leer y escribir archivos, usar la red y llamar a las integraciones instaladas.

## Instalación y uso

```console
python -m pip install .
mux examples/hola_mundo.mux
mux --check examples/hola_mundo.mux
python -m mux_lang examples/hola_mundo.mux
```

Consulta [README.md](README.md), [INSTALL.md](INSTALL.md) y [STDLIB_REFERENCE.md](STDLIB_REFERENCE.md).
