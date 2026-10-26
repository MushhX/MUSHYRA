# Cambios

## [2.0.0] - 2026-10-26

### Renombrado

- El lenguaje y sus herramientas pasan a llamarse MUSHYRA. `myr` y `myr-pkg` son los comandos principales; `mux` y `mux-pkg` siguen como alias compatibles.
- `.myr` pasa a ser la extensión principal. Se siguen leyendo archivos `.mux`, configuraciones anteriores y paquetes con entradas `.mux`.
- El paquete de instalación se llama `mushyra`; el módulo Python `mux_lang` y el repositorio conservan sus rutas para no romper imports ni enlaces existentes.
- Las expresiones `lambda` permiten crear funciones anónimas con parámetros posicionales o con nombre y cierres léxicos.

## [1.2.0] - 2026-10-26

### Añadido

- AST con spans, errores JSON, linter, formatter, watch mode, configuración de usuario e historial del REPL.
- Resolución léxica anticipada, semántica explícita de valores, trazas con ubicación de llamada y definición, y depurador por línea.
- Presupuestos de pasos, llamadas, salida y asignaciones estimadas; plazos cooperativos, sandbox de capacidades y caché acotada de AST importados.
- Servidor LSP integrado para VS Code con diagnósticos, finalización, navegación y símbolos del documento.
- Comando `mux init` para generar un proyecto mínimo sin reemplazar archivos existentes.
- Parámetros por defecto, argumentos con nombre y argumentos variádicos en funciones Mux.
- Tuplas inmutables, desempaquetado de secuencias y diccionarios con patrones anidados y slices, incluido el reemplazo de slices en listas.
- Módulo `sequence` con `map`, `filter`, `enumerate`, `zip`, `any`, `all` y `sum`, con callbacks Mux y límites de pasos y memoria.
- Comprehensions de listas y diccionarios con ámbito temporal y filtro opcional; patrones de desempaquetado para diccionarios.
- Breakpoints condicionales, expresiones observadas e inspección de ámbitos y módulos en el depurador.
- Plantillas `app` y `library` para `mux init`.
- Módulos `path`, `csv` y `toml` con límites de tamaño y respeto de `--sandbox-root`.
- Módulo `time` con parsing ISO-8601, conversión IANA, aritmética de fechas y unidades de duración.
- Códigos de diagnóstico estables para lexer, parser, resolver e intérprete, documentados en `DIAGNOSTICS.md`.
- Benchmark para bucles, llamadas y colecciones; `--time` informa pasos y rendimiento observado.
- Paquetes firmados Ed25519, índices configurables, hash por archivo, creación de ZIP, lockfiles y auditoría.
- EBNF, guía de seguridad, referencia ampliada, benchmark, soporte de VS Code y CI multiplataforma.

### Cambiado

- Las instalaciones de paquetes desde HTTPS requieren firma Ed25519 además de SHA-256 por defecto. Para un ZIP directo, `mux-pkg install --allow-unsigned` permite omitir la firma de forma explícita y conserva la validación SHA-256.
- Se centraliza la metadata de distribución en `pyproject.toml`; se retira del repositorio la carpeta generada `mux_lang.egg-info`.

### Seguridad

- HTTP/ZIP se limita a hosts públicos, valida redirecciones y acota tamaños.
- Los manifiestos remotos firmados vinculan hashes de los archivos publicados.
- SQLite bajo `--sandbox-root` bloquea instrucciones que pueden abrir rutas externas.
- El modo `--sandbox` bloquea red, correo, entorno y módulos de bots; se documenta que no sustituye el aislamiento del sistema operativo.
