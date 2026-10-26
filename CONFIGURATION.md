# Configuración de la CLI

Mux carga configuración JSON al iniciar. La ruta se toma de `--config`, después de `MUX_CONFIG`; si ninguna está definida, usa `AppData/Roaming/Mux/config.json` en Windows o `$XDG_CONFIG_HOME/mux/config.json` (por defecto `~/.config/mux/config.json`) en Linux/macOS.

Ejemplo:

```json
{
  "max_steps": 100000,
  "max_call_depth": 128,
  "max_output_bytes": 10485760,
  "max_allocation_bytes": 67108864,
  "timeout_seconds": 30,
  "sandbox_root": "./proyecto",
  "sandbox": false,
  "diagnostics_format": "text",
  "watch_interval": 0.5
}
```

Claves disponibles:

- `max_steps`: entero positivo; omítelo para no imponer límite.
- `max_call_depth`: entero entre `1` y `128`, por defecto `128`.
- `sandbox_root`: ruta de texto para limitar archivos e imports locales.
- `sandbox`: `true` para bloquear red, correo, variables de entorno y módulos de bots. Si falta `sandbox_root`, se limita al directorio del programa o al actual en REPL/stdin.
- `max_output_bytes`: bytes UTF-8 máximos escritos por el programa; predeterminado 10 MiB.
- `max_allocation_bytes`: presupuesto aproximado de memoria asignada a valores Mux; predeterminado 64 MiB. No es una medición del heap del proceso.
- `timeout_seconds`: plazo cooperativo opcional, entre `0.001` y `86400` segundos. No puede interrumpir callbacks síncronos externos que no admitan timeout.
- `diagnostics_format`: `text` o `json`.
- `watch_interval`: número entre `0.1` y `60` segundos.

Las opciones CLI prevalecen sobre el archivo de configuración. Los ajustes se validan al arrancar; se rechazan claves desconocidas, JSON no válido y archivos de más de 1 MiB. No pongas secretos en este archivo: los programas pueden leer variables de entorno con `env`.
