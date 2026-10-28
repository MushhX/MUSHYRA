# Diagnósticos MUSHYRA

Los errores de `myr` y los diagnósticos LSP incluyen un código estable. El texto del mensaje puede aclararse entre versiones; el código identifica la categoría del problema.

| Código | Categoría |
| --- | --- |
| `MYR1001` | Entrada léxica: carácter, literal, tamaño de fuente o cantidad de tokens no válida |
| `MYR1002` | Sintaxis del programa |
| `MYR2001` | Resolución estática de nombres y ámbitos |
| `MYR3001` | Error durante la ejecución del programa |
| `MYR100`–`MYR105` | Advertencias del linter: claves duplicadas, código inalcanzable, nombres no declarados, imports o variables no usados y cláusulas `case`/`catch` inalcanzables |
| `MYR000` | Error genérico de una herramienta o integración que aún no asigna una categoría propia |

`myr --diagnostics-format json` devuelve el código junto con mensaje, ruta, línea, columna y contexto. El servidor LSP comunica el mismo código en cada diagnóstico.
