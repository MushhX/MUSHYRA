# Configuración de la CLI

Mux carga configuración JSON al iniciar. La ruta se toma de `--config`, después de `MUX_CONFIG`; si ninguna está definida, usa `AppData/Roaming/Mux/config.json` en Windows o `$XDG_CONFIG_HOME/mux/config.json` (por defecto `~/.config/mux/config.json`) en Linux/macOS.

Ejemplo:

```json
{
  "max_steps": 100000,
  "max_call_depth": 128,
  "sandbox_root": "./proyecto",
  "diagnostics_format": "text",
  "watch_interval": 0.5
}
```

Claves disponibles:

- `max_steps`: entero positivo; omítelo para no imponer límite.
- `max_call_depth`: entero entre `1` y `128`, por defecto `128`.
- `sandbox_root`: ruta de texto para limitar archivos e imports locales.
- `diagnostics_format`: `text` o `json`.
- `watch_interval`: número entre `0.1` y `60` segundos.

Las opciones CLI prevalecen sobre el archivo de configuración. Los ajustes se validan al arrancar; se rechazan claves desconocidas, JSON no válido y archivos de más de 1 MiB. No pongas secretos en este archivo: los programas pueden leer variables de entorno con `env`.
