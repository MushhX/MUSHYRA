# Características de Mux

## Lenguaje

- Variables con `let`, asignación posterior y valores `null`, booleanos, números y strings.
- Listas y diccionarios, índices y asignación por índice o atributo.
- Operadores aritméticos, comparación estricta, `&&`, `||` y `!` con evaluación corta.
- `if`/`elif`/`else`, `repeat`, `N times [do]`, `while`, `for`, `each`, `until`, `unless` y `loop`.
- `break` y `continue` en bucles; `pass`; funciones, `return`, `global` y `nonlocal`.
- Llamadas `print`, `input`, `ask`, `len`, `type`, `str`, `int`, `float`, `range`, `assert`, `show`, `say`, `wait` y `exit`.
- Imports completos, alias y `from ... import ...`.
- Saltos de línea como separadores y `end` para cerrar bloques.

El lenguaje todavía no incluye clases, excepciones propias, generadores, async/await, comprensión de listas, slicing ni un sistema de tipos estático.

## Intérprete y CLI

- Lexer y parser recursivo con spans por nodo, errores de ejecución contextualizados e imports con contexto.
- API de intérprete con entrada/salida inyectables, presupuesto compartido de pasos, cancelación, límites de colecciones y profundidad de llamada.
- CLI para ejecutar archivos `.mux`, leer stdin, REPL con historial, comprobar sintaxis, mostrar tokens/AST, lint, formato, watch, argumentos de programa y diagnósticos JSON.
- Configuración JSON por usuario y opciones de sandbox de rutas.

## Módulos

Incluye 17 módulos nativos: `math`, `random`, `http`, `filesystem`, `json`, `crypto`, `regex`, `strings`, `time`, `database`, `email`, `console`, `env`, `web`, `discord_bot`, `telegram_bot` y `whatsapp`. Las integraciones de Flask, Discord, Telegram, Twilio y AES-GCM usan extras opcionales. La referencia describe las funciones y sus requisitos.

## Herramientas

- `mux-pkg` instala paquetes locales o remotos con HTTPS, SHA-256, firmas Ed25519, registro configurable, lockfiles e inspección de integridad.
- `build_exe.py` empaqueta la plataforma actual con PyInstaller.
- `build_installer.py` genera el instalador Windows con Inno Setup.
- `create_portable_installer.py` crea un ZIP reproducible para la plataforma actual.
- `benchmarks/sum_100k.mux` permite comparar tiempos con `mux --time`.

## Límites actuales

- Clases, excepciones del lenguaje, generadores, async/await, slicing y sistema de tipos estático.
- Un registro público alojado y una clave de firma oficial requieren infraestructura y operación fuera del repositorio.
- Un depurador interactivo, profiler dedicado y extensiones de editor aún no están incluidos.
- `--sandbox-root` limita rutas de archivos; no aísla código hostil ni limita la red o extensiones nativas.
