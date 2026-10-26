# Hoja de ruta

La versión publicada más reciente es 2.0.0. Esta lista separa las capacidades incorporadas de las siguientes decisiones de producto; no promete fechas.

## Incorporado en esta iteración

- AST compatible con tuplas y spans de origen; errores recuperables en el REPL.
- Límites de pasos, profundidad, colecciones, archivos, JSON, HTTP, regex y resultados SQLite.
- Resolución léxica, semántica explícita de valores, depurador paso a paso, límites de salida/asignación y sandbox de módulos nativos.
- Servidor LSP integrado y extensión VS Code para diagnósticos y navegación básica del código.
- Caché de AST de importaciones y benchmarks de bucles, llamadas y colecciones con conteo de pasos.
- CLI con configuración, `--check`, `--lint`, `--format`, `--watch`, argumentos de script y diagnósticos JSON.
- Referencia EBNF, seguridad, configuración, benchmark y documentación de módulos.
- Suite automatizada, fuzzing basado en propiedades y CI multiplataforma con compilación de paquetes.
- Gestor con SemVer, hashes por archivo, firmas Ed25519, índice configurable, lockfiles, empaquetado e inspección de integridad.
- Guía de sintaxis y snippets para VS Code.
- Argumentos de función por defecto, con nombre y variádicos; tuplas, desempaquetado de patrones y slices.
- Funciones anónimas `lambda` con expresiones, cierres léxicos y validación estática de nombres.
- `match`/`case` con captura de nombres, patrones literales y de colecciones, guardas y `else`.

## Siguientes áreas

- Decidir semántica y compatibilidad de clases, excepciones propias, generadores y concurrencia del lenguaje; `lambda` ya está incorporado.
- Evaluar bytecode/VM únicamente después de medir el árbol de ejecución con cargas representativas.
- Publicar un índice operado por el proyecto y gestionar su raíz de confianza y rotación de claves.
- Ampliar telemetría opt-in y documentación de rendimiento sin recopilar datos por defecto.
- Evaluar otros editores después de estabilizar la gramática y las contribuciones de la extensión VS Code.

## Compatibilidad

La CI cubre Python 3.8, 3.10, 3.12 y 3.14 en Linux, además de Python 3.12 en Windows y macOS. Los extras de integraciones externas se mantienen opcionales.
