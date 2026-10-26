# Notas de versión

## 1.2.0 — cambios del código fuente

- AST con spans, errores JSON, parser con límites y errores de ejecución con contexto de función/import.
- Resolución de ámbitos antes de ejecutar, semántica de operadores definida y trazas que incluyen llamada y definición.
- Depurador `--debugger`, caché LRU de AST de módulos con hash de contenido y benchmark del runtime.
- Servidor de lenguaje `mux --lsp` y funciones semánticas en la extensión VS Code.
- CLI `mux archivo.mux` con configuración, linter, formatter, watch, argumentos, REPL con historial y diagnósticos.
- Presupuestos de salida/asignaciones, timeout cooperativo, sandbox de capacidades, validación HTTP/JSON y operaciones SQLite acotadas.
- Gestor con SemVer, HTTPS, SHA-256, firmas Ed25519, empaquetado, índices configurables, lockfiles y auditoría.
- Suite automatizada y CI para Linux, Windows, macOS, varias versiones de Python y validación de artefactos.
- Especificación EBNF, guía de seguridad, configuración, referencia, benchmark y sintaxis/snippets para VS Code.
- Versión única en `mux_lang/_version.py`; los metadatos generados `mux_lang.egg-info` dejan de versionarse.

Las instalaciones de paquetes HTTPS requieren firma Ed25519 por defecto; `--allow-unsigned` permite optar explícitamente por comprobar solo SHA-256. No se ha configurado un registro público ni una clave oficial de firma. Los artefactos binarios se generan localmente; estas notas no afirman que haya una release publicada ni que se hayan construido binarios para todas las plataformas.
