# Contribuir

Gracias por mejorar Mux. Los cambios deben mantener la gramática pequeña, los errores legibles y la documentación alineada con el comportamiento.

## Preparar el entorno

```console
git clone https://github.com/MushhX/Mux.git
cd Mux
python -m pip install -e .
mux examples/hola_mundo.mux
```

## Estructura

- `mux_lang/lexer.py`: tokens y ubicaciones de origen.
- `mux_lang/parser.py`: gramática y AST.
- `mux_lang/interpreter.py`: evaluación, scopes y carga de módulos.
- `mux_lang/native_stdlib.py`: módulos nativos.
- `mux_lang/cli.py`: CLI y REPL.
- `mux_lang/package_manager.py`: instalación local y ZIP verificado.
- `examples/`: programas de muestra.
- `build_*.py`, `create_*.py`: empaquetado y distribución.

## Cambios

1. Abre un issue para cambios grandes de sintaxis o API.
2. Crea una rama descriptiva.
3. Mantén los cambios enfocados y añade ejemplos cuando cambie el lenguaje.
4. Actualiza la documentación afectada.
5. Añade cobertura para cambios de lexer, parser, runtime, CLI o paquetes.
6. Antes de proponer el cambio, ejecuta la suite y los flujos afectados; describe los comandos y plataformas comprobados.

## Guías de implementación

- Conserva compatibilidad de sintaxis salvo que el cambio documente una migración.
- No conviertas errores de usuario en tracebacks sin contexto.
- Valida entradas externas y usa parámetros SQL en vez de concatenar valores.
- Mantén las credenciales en variables de entorno y las dependencias opcionales en extras.
- No afirmes que una plataforma o integración está soportada sin comprobar su flujo completo.

## Pull requests

Incluye el objetivo, los cambios de comportamiento, comandos de validación ejecutados y cualquier limitación pendiente. Evita adjuntar secretos, bases de datos locales, cachés o ejecutables generados.

La CI ejecuta la suite en Linux, Windows y macOS y compila los artefactos fuente y wheel. Los cambios que necesiten secretos, una clave de publicación o un servicio externo deben describir esa dependencia sin añadir credenciales al repositorio.
