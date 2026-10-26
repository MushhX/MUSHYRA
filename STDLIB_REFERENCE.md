# Referencia de la biblioteca estándar

Todos los módulos se importan con `import nombre`. Las funciones también quedan disponibles sin prefijo, por compatibilidad con Mux. Con `import nombre as alias`, accede a ellas como `alias.funcion(...)`.

Las rutas relativas de `filesystem`, `json`, `database` y adjuntos de correo se resuelven desde el directorio del archivo Mux.

## `math`

Constantes `pi`, `e`; funciones `abs(x)`, `max(x, ...)`, `min(x, ...)`, `pow(x, y)`, `sqrt(x)`, `floor(x)`, `ceil(x)` y `round(x[, decimales])`.

## `random`

`randint(min, max)`, `random()`, `choice(coleccion)`, `shuffle(lista)`, `sample(coleccion, cantidad)` y `seed(valor)`. `shuffle` modifica y devuelve la misma lista.

## `env`

`get(nombre[, predeterminado])` lee una variable de entorno y devuelve `null` si no existe; `require(nombre)` falla con un error legible si falta o está vacía; `has(nombre)` comprueba si está definida. El módulo no permite modificar el entorno del proceso.

## `http`

- `get(url[, headers[, timeout]])`
- `post(url, datos[, headers[, timeout]])`

Solo admite URL HTTP/HTTPS absolutas. Los diccionarios/listas enviados con `post` se codifican como JSON. La respuesta es un diccionario con `status`, `headers`, `body` y `json`; `json` vale `null` si el cuerpo no contiene JSON válido. La lectura se limita a 10 MiB por respuesta.

## `filesystem`

`read(ruta[, encoding])`, `write(ruta, contenido[, encoding])`, `append(ruta, contenido[, encoding])`, `exists(ruta)`, `remove_file(ruta)`, `list_dir(ruta)`, `create_dir(ruta)` y `get_size(ruta)`. `write` y `append` crean los directorios padre. `remove_file` elimina archivos, no directorios.

## `json`

`parse(texto)`, `stringify(valor)`, `pretty(valor)`, `load(ruta)` y `save(ruta, valor)`. `stringify` produce JSON compacto; `save` escribe JSON con indentación.

## `crypto`

`hash_md5(texto)`, `hash_sha256(texto)`, `encode_base64(texto)`, `decode_base64(texto)`, `generate_uuid()`, `encrypt(texto, clave)` y `decrypt(texto_cifrado, clave)`. El cifrado usa AES-GCM y PBKDF2; requiere `python -m pip install "mux-lang[crypto]"` (o la instalación equivalente desde el repositorio). MD5 se ofrece por compatibilidad, no para almacenar contraseñas.

## `regex`

`match(patron, texto)`, `find_all(patron, texto)`, `replace(patron, reemplazo, texto)`, `split(patron, texto)`, `validate_email(email)`, `validate_url(url)`, `validate_phone(telefono)`, `extract_numbers(texto)` y `extract_emails(texto)`. Las validaciones son comprobaciones de formato sencillas; no verifican que una dirección exista.

## `strings`

`reverse(texto)`, `capitalize(texto)`, `count(texto, busqueda)`, `starts_with(texto, prefijo)`, `ends_with(texto, sufijo)`, `contains(texto, busqueda)`, `repeat(texto, veces)`, `pad_left(texto, longitud[, relleno])`, `pad_right(texto, longitud[, relleno])`, `trim_left(texto)`, `trim_right(texto)`, `to_ascii(texto)` y `from_ascii(codigos)`. `to_ascii`/`from_ascii` convierten puntos de código Unicode; `repeat` limita el resultado a diez millones de caracteres.

## `time`

`now()` y `timestamp()` devuelven segundos Unix; `sleep(segundos)` espera; `format_date(timestamp[, formato])` usa directivas `strftime`; `get_year()`, `get_month()`, `get_day()`, `get_hour()`, `get_minute()` y `get_second()` consultan hora local; `measure_time(funcion)` ejecuta una función sin argumentos y devuelve segundos transcurridos.

## `database`

Usa SQLite local. `connect(ruta)` abre una conexión; `create_table(tabla, columnas)` crea columnas de texto y trata `id` como clave primaria autoincremental; `insert(tabla, valores)`, `select(tabla[, condicion])`, `update(tabla, valores, condicion)`, `delete(tabla, condicion)`, `execute(sql[, parametros])` y `close([conexion])`.

Las condiciones de `select`/`update`/`delete` admiten una comparación sencilla: `"edad >= 18"`, `"nombre = 'Ana'"`. `delete` exige condición. Para consultas más complejas usa `execute` con parámetros como lista; no concatene datos externos dentro del SQL.

```mux
import database as db
let conexion = db.connect("datos.sqlite")
db.create_table("usuarios", ["id", "nombre", "edad"])
db.insert("usuarios", {"nombre": "Ana", "edad": 25})
let filas = db.select("usuarios", "edad >= 18")
db.close(conexion)
```

## `email`

`configure_smtp(host, puerto, usuario, password)`, `send(destinatario, asunto, texto)`, `send_html(destinatario, asunto, html)` y `send_with_attachment(destinatario, asunto, texto, ruta)`. El envío realiza una conexión SMTP real; usa TLS implícito en el puerto 465 y STARTTLS en otros puertos. Mantén las credenciales fuera del código fuente.

## `console`

`clear()`, `color(texto, color)`, `bold(texto)`, `italic(texto)`, `underline(texto)`, `progress_bar(actual, total)`, `table(filas)`, `menu(opciones)`, `confirm(mensaje)` y `spinner(mensaje)`. Los colores admitidos son black, red, green, yellow, blue, magenta, cyan y white. `menu` devuelve la opción elegida empezando en 1.

## `web` (extra `web`)

Requiere Flask: `crear_app()`, `ruta(app, path, handler)` e `iniciar(app, puerto)`. El handler de ruta es una función Mux sin argumentos que devuelve el cuerpo de la respuesta. El servidor enlaza a `127.0.0.1`.

## `discord_bot` (extra `discord`)

Requiere `discord.py`: `crear_bot(token)`, `comando(bot, nombre, handler)` e `iniciar_bot(bot)`. El handler Mux no recibe argumentos. Activa el intent de contenido de mensajes en el portal de Discord si los comandos por prefijo no llegan.

## `telegram_bot` (extra `telegram`)

Requiere `python-telegram-bot`: `crear_bot(token)`, `comando(bot, nombre, handler)` e `iniciar_bot(bot)`. El handler Mux no recibe argumentos.

## `whatsapp` (extra `whatsapp`)

Requiere Twilio. `send(destinatario, mensaje)` lee `MUX_TWILIO_ACCOUNT_SID`, `MUX_TWILIO_AUTH_TOKEN` y, opcionalmente, `MUX_TWILIO_WHATSAPP_FROM` del entorno. Devuelve `sid` y `status` del mensaje aceptado por Twilio.
