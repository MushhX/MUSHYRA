# Cambios

## [1.2.0] - 2026-10-26

### Añadido

- AST con spans, errores JSON, linter, formatter, watch mode, configuración de usuario e historial del REPL.
- Presupuestos de pasos y llamadas, cancelación cooperativa, límites de recursos y controles de rutas.
- Paquetes firmados Ed25519, índices configurables, hash por archivo, creación de ZIP, lockfiles y auditoría.
- EBNF, guía de seguridad, referencia ampliada, benchmark, soporte de VS Code y CI multiplataforma.

### Cambiado

- Las instalaciones de paquetes desde HTTPS requieren firma Ed25519 además de SHA-256 por defecto. Para un ZIP directo, `mux-pkg install --allow-unsigned` permite omitir la firma de forma explícita y conserva la validación SHA-256.
- Se centraliza la metadata de distribución en `pyproject.toml`; se retira del repositorio la carpeta generada `mux_lang.egg-info`.

### Seguridad

- HTTP/ZIP se limita a hosts públicos, valida redirecciones y acota tamaños.
- Los manifiestos remotos firmados vinculan hashes de los archivos publicados.
- SQLite bajo `--sandbox-root` bloquea instrucciones que pueden abrir rutas externas.
