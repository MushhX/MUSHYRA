# Modelo de seguridad

Mux está diseñado para ejecutar programas locales de confianza. El intérprete no es una máquina virtual aislada para ejecutar código hostil: las funciones nativas permiten acceder al sistema de archivos, a SQLite y a la red.

## Controles disponibles

- `mux --sandbox-root DIR archivo.mux` restringe las rutas usadas por `filesystem`, `json`, `database`, adjuntos de correo e imports locales a `DIR`. Las rutas se resuelven antes de comprobar la pertenencia, incluidos los enlaces simbólicos existentes. En ese modo, `database.execute` rechaza `ATTACH`, `DETACH`, `PRAGMA` y `VACUUM INTO`, que pueden abrir rutas externas.
- El sandbox de rutas no limita llamadas de red, imports nativos, memoria del proceso, procesos del sistema ni extensiones opcionales. No lo uses como frontera de seguridad para código no confiable.
- HTTP bloquea por defecto direcciones privadas, locales y reservadas y valida cada redirección. Para conectar deliberadamente con un servicio local, pasa `allow_private=true` en la llamada HTTP. La resolución DNS y la conexión usan la API estándar de Python; entornos con DNS controlado por un atacante deben aislarse además a nivel de red.
- `--max-steps` limita nodos evaluados y pasos de bucle. `--max-call-depth` (1–128, predeterminado 128) limita recursión. El parser también limita el anidamiento estructural y de expresiones. Estos límites no interrumpen una extensión nativa que se quede bloqueada.
- Las respuestas HTTP, archivos, JSON, expresiones regulares, adjuntos y colecciones tienen límites documentados en la referencia estándar.
- Los paquetes remotos se descargan solo por HTTPS y requieren SHA-256 y una firma Ed25519 de una clave del trust store. La firma del manifiesto incluye hashes de cada archivo. `--allow-unsigned` desactiva explícitamente la firma para instalaciones directas por HTTPS y se apoya solo en SHA-256; un hash comprueba integridad frente a un valor esperado, pero no prueba quién publicó el paquete.

## Secretos y criptografía

No guardes tokens ni contraseñas en archivos `.mux`, ejemplos, historial del REPL o repositorios. Usa variables de entorno y `env.require`. `crypto.password_hash` usa scrypt; `hash_md5` se conserva por compatibilidad y no sirve para almacenar contraseñas. `crypto.encrypt` usa AES-GCM y deriva una clave mediante PBKDF2.

## Publicación de paquetes

El repositorio no opera un registro público ni contiene una clave privada de publicación. Antes de distribuir paquetes, configura una raíz de confianza fuera del paquete y verifica firmas Ed25519 de índice y manifiesto además de los hashes. El proceso de firma y el almacenamiento de claves privadas deben vivir en CI/secrets del editor, nunca en este repositorio. Consulta [PACKAGE_REGISTRY.md](PACKAGE_REGISTRY.md) para el formato y el proceso.
