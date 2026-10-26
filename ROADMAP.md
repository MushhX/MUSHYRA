# Hoja de ruta

La versión de desarrollo pasa a 1.2.0. Esta lista separa las capacidades incorporadas de las siguientes decisiones de producto; no promete fechas.

## Incorporado en esta iteración

- AST compatible con tuplas y spans de origen; errores recuperables en el REPL.
- Límites de pasos, profundidad, colecciones, archivos, JSON, HTTP, regex y resultados SQLite.
- CLI con configuración, `--check`, `--lint`, `--format`, `--watch`, argumentos de script y diagnósticos JSON.
- Referencia EBNF, seguridad, configuración, benchmark y documentación de módulos.
- Suite automatizada, fuzzing basado en propiedades y CI multiplataforma con compilación de paquetes.
- Gestor con SemVer, hashes por archivo, firmas Ed25519, índice configurable, lockfiles, empaquetado e inspección de integridad.
- Guía de sintaxis y snippets para VS Code.

## Siguientes áreas

- Decidir semántica y compatibilidad de clases, excepciones propias, slicing y valores por defecto.
- Añadir un depurador paso a paso y un perfilador con spans de origen.
- Publicar un índice operado por el proyecto y gestionar su raíz de confianza y rotación de claves.
- Ampliar telemetría opt-in y documentación de rendimiento sin recopilar datos por defecto.
- Evaluar otros editores después de estabilizar la gramática y las contribuciones de la extensión VS Code.

## Compatibilidad

La CI cubre Python 3.8, 3.10, 3.12 y 3.14 en Linux, además de Python 3.12 en Windows y macOS. Los extras de integraciones externas se mantienen opcionales.
