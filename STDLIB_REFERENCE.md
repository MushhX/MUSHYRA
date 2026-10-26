# Referencia de la biblioteca estándar

Todos los módulos se importan con `import nombre`. Las funciones también quedan disponibles sin prefijo por compatibilidad con Mux. Con `import nombre as alias`, accede a ellas como `alias.funcion(...)`.

Las rutas relativas se resuelven desde el directorio del programa. `mux --sandbox-root DIR archivo.mux` restringe archivos y módulos locales a `DIR`; consulta [SECURITY.md](SECURITY.md) para conocer sus límites.

## `math`

Constantes `pi`, `e`; funciones `abs(x)`, `max(x, ...)`, `min(x, ...)`, `pow(x, y)`, `sqrt(x)`, `floor(x)`, `ceil(x)` y `round(x[, decimales])`.

## `random`

`randint(min, max)`, `random()`, `choice(coleccion)`, `shuffle(lista)`, `sample(coleccion, cantidad)` y `seed(valor)`. `shuffle` modifica y devuelve la misma lista. Este módulo usa un generador pseudoaleatorio y no sirve para crear credenciales.

## `sequence`

`map(funcion, coleccion)` y `filter(funcion, coleccion)` devuelven listas; `enumerate(coleccion[, inicio])` devuelve pares `(indice, valor)`; `zip(coleccion1, coleccion2[, ...])` devuelve tuplas hasta terminar la colección más corta. `any(coleccion)` y `all(coleccion)` devuelven booleanos con evaluación corta; `sum(coleccion)` suma números. Acepta listas, tuplas, strings, rangos y diccionarios (se recorren sus claves). Cada entrada se procesa con el presupuesto del intérprete y se limita a un millón de elementos. `map` y `filter` llaman funciones Mux y nativas.

```mux
import sequence as seq
func doble(valor)
    return valor * 2
end
let dobles = seq.map(doble, [1, 2, 3])
```

## `path`

`join(parte, ...)`, `normalize(ruta)`, `basename(ruta)`, `dirname(ruta)`, `stem(ruta)`, `extension(ruta)`, `is_absolute(ruta)` y `relative(base, destino)` usan la sintaxis de rutas de la plataforma actual. No acceden al sistema de archivos.

## `csv`

`read(ruta[, delimitador])` devuelve filas como listas de strings; `write(ruta, filas[, delimitador])` escribe filas atómicamente. El delimitador debe ser un carácter. Lectura y escritura están limitadas a 10 MiB, y el acceso a rutas respeta `--sandbox-root`.

## `toml`

`loads(texto)` analiza un string y `load(ruta)` lee un archivo. Los datos tienen límites de 10 MiB, 64 niveles de anidamiento y 100 000 elementos. Python 3.11 o posterior incluye el parser; en versiones anteriores instala `mux-lang[toml]`.

## `env`

`get(nombre[, predeterminado])` lee una variable de entorno y devuelve `null` si no existe; `require(nombre)` falla con un error legible si falta o está vacía; `has(nombre)` comprueba si está definida. El módulo no permite modificar el entorno.

## `http`

- `get(url[, headers[, timeout[, allow_private]]])`
- `post(url, datos[, headers[, timeout[, allow_private]]])`

Admite URL HTTP/HTTPS absolutas sin credenciales embebidas. Bloquea direcciones privadas/locales por defecto, permite hasta cinco redirecciones y bloquea degradar HTTPS a HTTP. `allow_private=true` permite un destino local de confianza. Timeout: 0–300 segundos. Cuerpo enviado y respuesta: máximo 10 MiB. Diccionarios/listas enviados con `post` se codifican como JSON. La respuesta incluye `status`, `headers`, `body` y `json`; `json` vale `null` si el cuerpo no es JSON válido.

## `filesystem`

`read(ruta[, encoding])`, `write(ruta, contenido[, encoding])`, `append(ruta, contenido[, encoding])`, `exists(ruta)`, `remove_file(ruta)`, `list_dir(ruta)`, `create_dir(ruta)` y `get_size(ruta)`. `write` usa reemplazo atómico; `write` y `append` crean directorios padre. `read` se limita a 10 MiB para acotar strings; las escrituras se limitan a 50 MiB y `list_dir` a 100 000 entradas. `remove_file` elimina archivos, no directorios.

## `json`

`parse(texto)`, `stringify(valor)`, `pretty(valor)`, `load(ruta)` y `save(ruta, valor)`. `stringify` produce JSON compacto; `save` escribe JSON indentado de forma atómica. Carga máxima: 10 MiB. Se rechazan constantes no estándar y claves de objeto duplicadas.

## `crypto`

`hash_md5(texto)`, `hash_sha256(texto)`, `encode_base64(texto)`, `decode_base64(texto)`, `generate_uuid()`, `generate_token([bytes])`, `password_hash(password)`, `password_verify(password, hash)`, `encrypt(texto, clave)` y `decrypt(texto_cifrado, clave)`. `generate_token` usa `secrets`; `password_hash`/`password_verify` usan scrypt; el cifrado usa AES-GCM y PBKDF2 y requiere instalar `mux-lang[crypto]`. MD5 se conserva por compatibilidad, no para almacenar contraseñas.

## `regex`

`match(patron, texto)`, `find_all(patron, texto)`, `replace(patron, reemplazo, texto)`, `split(patron, texto)`, `validate_email(email)`, `validate_url(url)`, `validate_phone(telefono)`, `extract_numbers(texto)` y `extract_emails(texto)`. Patrón máximo: 512 caracteres; entrada máxima: 64 Ki caracteres; resultados máximos: 100 000; salida materializada máxima: 10 Mi caracteres. El extra `mux-lang[regex]` activa timeouts de 100 ms. Sin él se rechazan patrones con construcciones conocidas por causar retroceso exponencial, pero el motor estándar no garantiza timeout. Las validaciones de formato no comprueban que el destino exista.

## `strings`

`reverse(texto)`, `capitalize(texto)`, `count(texto, busqueda)`, `starts_with(texto, prefijo)`, `ends_with(texto, sufijo)`, `contains(texto, busqueda)`, `repeat(texto, veces)`, `pad_left(texto, longitud[, relleno])`, `pad_right(texto, longitud[, relleno])`, `trim_left(texto)`, `trim_right(texto)`, `to_ascii(texto)` y `from_ascii(codigos)`. `to_ascii`/`from_ascii` convierten puntos de código Unicode; la repetición limita el resultado a diez millones de caracteres.

## `time`

`now()` y `timestamp()` devuelven segundos Unix; `now_utc()` y `now_in_timezone(zona)` devuelven fechas ISO-8601. `parse_iso(fecha)` valida y normaliza una fecha; `to_timezone(fecha, zona)` convierte una fecha con offset explícito a una zona IANA. Las zonas IANA requieren Python 3.9 o posterior. `add_seconds(fecha, segundos)` calcula una fecha nueva y `duration_seconds(inicio, fin)` devuelve la diferencia en segundos. `seconds(n)`, `minutes(n)`, `hours(n)` y `days(n)` convierten duraciones a segundos. `format_date(timestamp[, formato])` usa hora local y `format_date_utc(timestamp[, formato])` UTC. `sleep(segundos)` espera hasta 300 segundos y responde a la cancelación del intérprete. `get_year()`, `get_month()`, `get_day()`, `get_hour()`, `get_minute()` y `get_second()` consultan hora local. `measure_time(funcion)` ejecuta una función sin argumentos y devuelve segundos transcurridos.

## `database`

SQLite local. `connect(ruta[, timeout])` activa claves foráneas, WAL y timeout configurable; `create_table(tabla, columnas)` crea columnas de texto y trata `id` como clave primaria autoincremental; `insert(tabla, valores)`, `select(tabla[, condicion[, limit[, offset]]])`, `update(tabla, valores, condicion)`, `delete(tabla, condicion)`, `execute(sql[, parametros])`, `begin()`, `commit()`, `rollback()`, `transaction(funcion)` y `close([conexion])`.

`select` devuelve páginas de hasta 10 000 filas; `execute` también limita resultados a 10 000. Los resultados están limitados a 10 MiB. Las condiciones sencillas aceptan, por ejemplo, `"edad >= 18"` o `"nombre = 'Ana'"`. `update` y `delete` requieren condición. `transaction(funcion)` confirma si la función termina bien y revierte si falla. Para consultas complejas usa `execute` con una lista de parámetros; no concatene datos externos en SQL. Con `--sandbox-root`, `execute` bloquea instrucciones `ATTACH`, `DETACH`, `PRAGMA` y `VACUUM INTO` para mantener la restricción de rutas.

```mux
import database as db
let conexion = db.connect("datos.sqlite", 5)
db.create_table("usuarios", ["id", "nombre", "edad"])
db.insert("usuarios", {"nombre": "Ana", "edad": 25})
let filas = db.select("usuarios", "edad >= 18", 100, 0)
db.close(conexion)
```

## `email`

`configure_smtp(host, puerto, usuario, password)`, `send(destinatario, asunto, texto)`, `send_html(destinatario, asunto, html)` y `send_with_attachment(destinatario, asunto, texto, ruta)`. Usa TLS implícito en el puerto 465 y STARTTLS en otros puertos, valida certificados y limita adjuntos a 10 MiB. Mantén las credenciales fuera del código fuente.

## `console`

`clear()`, `color(texto, color)`, `bold(texto)`, `italic(texto)`, `underline(texto)`, `progress_bar(actual, total)`, `table(filas)`, `menu(opciones)`, `confirm(mensaje)` y `spinner(mensaje)`. Los colores admitidos son black, red, green, yellow, blue, magenta, cyan y white. `NO_COLOR` desactiva secuencias ANSI; `FORCE_COLOR` las habilita.

## `web` (extra `web`)

Requiere Flask: `crear_app()`, `ruta(app, path, handler)` e `iniciar(app, puerto)`. El handler es una función Mux sin argumentos que devuelve el cuerpo. El servidor enlaza a `127.0.0.1`, con debug y reloader desactivados. El servidor integrado es para desarrollo; usa un servidor WSGI de producción para desplegar.

## `discord_bot` (extra `discord`)

Requiere `discord.py`: `crear_bot(token)`, `comando(bot, nombre, handler)` e `iniciar_bot(bot)`. El handler Mux no recibe argumentos. Los handlers se ejecutan fuera del event loop de Discord. Activa el intent de contenido de mensajes en el portal de Discord si los comandos por prefijo no llegan.

## `telegram_bot` (extra `telegram`)

Requiere `python-telegram-bot`: `crear_bot(token)`, `comando(bot, nombre, handler)` e `iniciar_bot(bot)`. El handler Mux no recibe argumentos y se ejecuta fuera del event loop.

## `whatsapp` (extra `whatsapp`)

Requiere Twilio. `send(destinatario, mensaje)` lee `MUX_TWILIO_ACCOUNT_SID`, `MUX_TWILIO_AUTH_TOKEN` y, opcionalmente, `MUX_TWILIO_WHATSAPP_FROM` del entorno. Devuelve `sid` y `status` del mensaje aceptado por Twilio.
