# Características de MUSHYRA

## Lenguaje

- Variables con `let`, asignación posterior y valores `null`, booleanos, números y strings.
- Listas, tuplas y diccionarios; comprensiones, índices, slices, desempaquetado de secuencias y diccionarios y asignación por índice, slice o atributo.
- Operadores aritméticos, comparación estricta, `&&`, `||` y `!` con evaluación corta.
- `if`/`elif`/`else`, `repeat`, `N times [do]`, `while`, `for`, `each`, `until`, `unless` y `loop`.
- `break` y `continue` en bucles; `pass`; funciones nombradas y anónimas (`lambda`), `return`, `global` y `nonlocal`.
- Llamadas `print`, `input`, `ask`, `len`, `type`, `str`, `int`, `float`, `range`, `assert`, `show`, `say`, `wait` y `exit`.
- Imports completos, alias y `from ... import ...`.
- Saltos de línea como separadores y `end` para cerrar bloques.

El lenguaje todavía no incluye clases, excepciones propias, generadores, async/await, `match` ni un sistema de tipos estático.

## Intérprete y CLI

- Lexer y parser recursivo con spans por nodo, errores de ejecución contextualizados e imports con contexto.
- API de intérprete con resolución previa de ámbitos, valores con semántica explícita, entrada/salida inyectables, presupuestos compartidos, cancelación y límite de profundidad.
- Presupuestos configurables de pasos, salida, asignaciones estimadas y duración; límites individuales de strings y colecciones.
- Códigos estables para errores léxicos, sintácticos, estáticos y de ejecución; la salida JSON y LSP los conservan.
- CLI `myr` para ejecutar archivos `.myr`, leer stdin, REPL con historial, comprobar sintaxis, tokens/AST, lint, formato, watch, argumentos, diagnósticos JSON y depurador por línea con breakpoints condicionales, watches y exploración de ámbitos/módulos.
- Configuración JSON por usuario, sandbox de rutas y modo estricto que deniega módulos nativos de red/entorno.
- Servidor de lenguaje por `myr --lsp` y extensión VS Code con diagnósticos, finalización, referencias, definición, símbolos y hover básico.
- Funciones con parámetros por defecto, argumentos con nombre y un parámetro variádico final, además de las llamadas posicionales existentes.
- `myr init [directorio]` crea una aplicación o una plantilla de biblioteca con README, sin sobrescribir archivos existentes.
- Autocompletado de opciones y rutas para Bash y PowerShell.

## Módulos

Incluye 21 módulos nativos: `math`, `random`, `sequence`, `path`, `csv`, `toml`, `http`, `filesystem`, `json`, `crypto`, `regex`, `strings`, `time`, `database`, `email`, `console`, `env`, `web`, `discord_bot`, `telegram_bot` y `whatsapp`. Las integraciones de Flask, Discord, Telegram, Twilio, TOML en Python anterior a 3.11 y AES-GCM usan extras opcionales. La referencia describe las funciones y sus requisitos.

## Herramientas

- `myr-pkg` instala paquetes locales o remotos con HTTPS, SHA-256, firmas Ed25519, registro configurable, lockfiles e inspección de integridad.
- `build_exe.py` empaqueta la plataforma actual con PyInstaller.
- `build_installer.py` genera el instalador Windows con Inno Setup.
- `create_portable_installer.py` crea un ZIP reproducible para la plataforma actual.
- `benchmarks/sum_100k.myr` y `benchmarks/interpreter_suite.myr` miden trabajo representativo con duración y pasos mediante `myr --time`.

## Límites actuales

- Clases/structs, excepciones propias, generadores, async/await, `match`, sistema de tipos estático y conjuntos/colas.
- Un registro público alojado y una clave de firma oficial requieren infraestructura y operación fuera del repositorio.
- El modo sandbox es una restricción de capacidades dentro del intérprete, no aísla código hostil al nivel del sistema operativo.
- El benchmark ofrece señales iniciales, no un profiler ni datos de pico de memoria.
