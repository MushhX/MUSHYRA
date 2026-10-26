# Diagnósticos MUSHYRA

Los errores de `myr` y los diagnósticos LSP incluyen un código estable. El texto del mensaje puede aclararse entre versiones; el código identifica la categoría del problema.

| Código | Categoría |
| --- | --- |
| `MUX1001` | Entrada léxica: carácter, literal, tamaño de fuente o cantidad de tokens no válida |
| `MUX1002` | Sintaxis del programa |
| `MUX2001` | Resolución estática de nombres y ámbitos |
| `MUX3001` | Error durante la ejecución del programa |
| `MUX100`–`MUX104` | Advertencias del linter: claves duplicadas, código inalcanzable, nombres no declarados e imports o variables no usados |
| `MUX000` | Error genérico de una herramienta o integración que aún no asigna una categoría propia |

`myr --diagnostics-format json` devuelve el código junto con mensaje, ruta, línea, columna y contexto. El servidor LSP comunica el mismo código en cada diagnóstico.
