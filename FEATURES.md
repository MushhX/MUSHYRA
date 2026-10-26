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

- Lexer y parser recursivo con ubicaciones de origen.
- Errores de ejecución con contexto de llamadas e imports.
- API de intérprete con entrada/salida inyectables y límite opcional de pasos.
- CLI para ejecutar archivos, leer stdin, REPL, comprobar sintaxis y mostrar tokens o AST.

## Módulos

Incluye 17 módulos nativos: `math`, `random`, `http`, `filesystem`, `json`, `crypto`, `regex`, `strings`, `time`, `database`, `email`, `console`, `env`, `web`, `discord_bot`, `telegram_bot` y `whatsapp`. Las integraciones de Flask, Discord, Telegram, Twilio y AES-GCM usan extras opcionales. La referencia describe las funciones y sus requisitos.

## Herramientas

- `mux-pkg` instala paquetes Mux locales o ZIP remotos con HTTPS y SHA-256.
- `build_exe.py` empaqueta la plataforma actual con PyInstaller.
- `build_installer.py` genera el instalador Windows con Inno Setup.
- `create_portable_installer.py` crea un ZIP reproducible para la plataforma actual.

## Áreas de desarrollo futuro

- Clases y excepciones del lenguaje.
- Módulos `os`/`sys` con permisos y límites definidos.
- Depurador y profiler.
- Índice remoto de paquetes firmado.
- Formateador, linter y soporte de editor.
- Cobertura de pruebas automatizadas y compatibilidad continua entre plataformas.
