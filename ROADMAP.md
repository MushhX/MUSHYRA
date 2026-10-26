# Plan de desarrollo

La versión declarada en el paquete es 1.1.0. Este archivo describe trabajo posible, no fechas ni compromisos de publicación.

## Lenguaje

- Diseñar clases y excepciones propias antes de añadirlas a la gramática.
- Definir slicing, valores por defecto y semántica de tipos de forma coherente.
- Añadir mejor soporte para Unicode y mensajes de error recuperables en el REPL.

## Calidad y herramientas

- Crear una suite de pruebas automatizadas para lexer, parser, intérprete, módulos, gestor y empaquetado.
- Incorporar lint, formato y comprobaciones multiplataforma en CI.
- Añadir depurador paso a paso y perfilado con líneas de origen.
- Documentar versiones soportadas de Python y dependencias opcionales.

## Paquetes y distribución

- Diseñar un índice remoto firmado y versionado antes de habilitar un catálogo.
- Definir resolución de dependencias, bloqueo de versiones y desinstalación segura.
- Publicar y verificar artefactos de Windows, macOS y Linux con hashes y procedencia.

## Editor

- Preparar resaltado, snippets y diagnóstico para editores comunes.
- Valorar formateador y linter después de estabilizar la gramática.
