# Modelo de seguridad

Mux está diseñado para ejecutar programas locales de confianza. El intérprete no es una máquina virtual aislada para ejecutar código hostil: las funciones nativas permiten acceder al sistema de archivos, a SQLite y a la red.

## Controles disponibles

- `mux --sandbox-root DIR archivo.mux` restringe rutas de `filesystem`, `json`, `database`, adjuntos e imports locales a `DIR`. En modo estricto, usa `mux --sandbox --sandbox-root DIR archivo.mux`; se permite una lista reducida de módulos nativos y se bloquean red, correo, entorno y bots.
- Si se omite `--sandbox-root` junto a `--sandbox`, el directorio del programa (o el directorio actual para stdin/REPL) se convierte en raíz permitida. `--sandbox-root` por sí solo conserva el comportamiento anterior: restringe rutas e imports, pero no deshabilita módulos de red.
- El modo estricto permite `math`, `random`, `sequence`, `path`, `csv`, `toml`, `strings`, `json`, `regex`, `time`, `console`, `filesystem` y `database`; las operaciones de `csv` y `toml` pasan por el control de rutas del intérprete.
- El modo sandbox es una política del intérprete, no una frontera de aislamiento del sistema operativo. Las rutas se resuelven antes de operar; un proceso hostil concurrente podría cambiar enlaces simbólicos entre la comprobación y la operación. Usa una cuenta o contenedor del sistema operativo para ejecutar código hostil.
- HTTP bloquea por defecto direcciones privadas, locales y reservadas y valida cada redirección. Para conectar deliberadamente con un servicio local, pasa `allow_private=true` en la llamada HTTP. La resolución DNS y la conexión usan la API estándar de Python; entornos con DNS controlado por un atacante deben aislarse además a nivel de red.
- `--max-steps` limita nodos evaluados y pasos de bucle. `--max-call-depth` (1–128, predeterminado 128) limita recursión. `--max-output-bytes` limita la salida UTF-8; `--max-allocation-bytes` contabiliza aproximadamente el crecimiento de valores; `--timeout-seconds` impone un plazo cooperativo.
- Los plazos se comprueban en cada paso, acotan timeouts de red/SQLite y se consultan durante `wait` e input interactivo. Los callbacks de entrada personalizados, streams no seleccionables, servidores web y extensiones nativas que no expongan timeouts no se pueden interrumpir a la fuerza; el plazo se detecta cuando devuelven.
- La salida, asignaciones estimadas, cadenas y colecciones tienen límites. También se limitan respuestas HTTP, archivos, JSON, expresiones regulares y adjuntos según la referencia estándar. El límite de asignación es una estimación, no una medición del heap de Python.
- Los paquetes remotos se descargan solo por HTTPS y requieren SHA-256 y una firma Ed25519 de una clave del trust store. La firma del manifiesto incluye hashes de cada archivo. `--allow-unsigned` desactiva explícitamente la firma para instalaciones directas por HTTPS y se apoya solo en SHA-256; un hash comprueba integridad frente a un valor esperado, pero no prueba quién publicó el paquete.

## Secretos y criptografía

No guardes tokens ni contraseñas en archivos `.mux`, ejemplos, historial del REPL o repositorios. Usa variables de entorno y `env.require`. `crypto.password_hash` usa scrypt; `hash_md5` se conserva por compatibilidad y no sirve para almacenar contraseñas. `crypto.encrypt` usa AES-GCM y deriva una clave mediante PBKDF2.

## Publicación de paquetes

El repositorio no opera un registro público ni contiene una clave privada de publicación. Antes de distribuir paquetes, configura una raíz de confianza fuera del paquete y verifica firmas Ed25519 de índice y manifiesto además de los hashes. El proceso de firma y el almacenamiento de claves privadas deben vivir en CI/secrets del editor, nunca en este repositorio. Consulta [PACKAGE_REGISTRY.md](PACKAGE_REGISTRY.md) para el formato y el proceso.
