# Referencia de Librería Estándar de Mux
**Creador: MushhX**

Mux incluye 15 módulos en su librería estándar para cubrir las necesidades más comunes de programación.

## 📚 Índice de Módulos

1. [math](#math) - Matemáticas
2. [http](#http) - Peticiones HTTP
3. [web](#web) - Desarrollo web
4. [discord_bot](#discord_bot) - Bots de Discord
5. [telegram_bot](#telegram_bot) - Bots de Telegram
6. [strings](#strings) - Manipulación de strings
7. [regex](#regex) - Expresiones regulares
8. [random](#random) - Números aleatorios
9. [database](#database) - Bases de datos
10. [filesystem](#filesystem) - Manejo de archivos
11. [crypto](#crypto) - Criptografía
12. [time](#time) - Tiempo y fechas
13. [json](#json) - Trabajar con JSON
14. [console](#console) - Consola mejorada
15. [email](#email) - Envío de emails

---

## math

Funciones matemáticas básicas y avanzadas.

```mux
import math

# Constantes
print(pi)  # 3.14159265359
print(e)   # 2.71828182846

# Funciones
abs(-15)        # Valor absoluto
max(10, 25)     # Máximo
min(10, 25)     # Mínimo
pow(2, 8)       # Potencia
sqrt(16)        # Raíz cuadrada
```

---

## http

Realizar peticiones HTTP.

```mux
import http

# GET request
let respuesta = get("https://api.example.com/data")

# POST request
let datos = {"nombre": "Ana", "edad": 25}
let respuesta = post("https://api.example.com/users", datos)
```

---

## web

Crear aplicaciones web.

```mux
import web

let app = crear_app()

func index_handler()
    return "<h1>¡Hola desde Mux!</h1>"
end

ruta(app, "/", index_handler)
iniciar(app, 5000)
```

---

## discord_bot

Crear bots de Discord.

```mux
import discord_bot

let bot = crear_bot("TU_TOKEN")

func saludar_handler()
    print("¡Hola desde Discord!")
end

comando(bot, "hola", saludar_handler)
iniciar_bot(bot)
```

---

## telegram_bot

Crear bots de Telegram.

```mux
import telegram_bot

let bot = crear_bot("TU_TOKEN")
comando(bot, "start", start_handler)
iniciar_bot(bot)
```

---

## strings

Manipulación avanzada de strings.

```mux
import strings

reverse("Hola")                    # Invertir
capitalize("hola mundo")           # Capitalizar
count("hola hola", "hola")        # Contar ocurrencias
starts_with("Hola", "Ho")         # Empieza con
ends_with("Hola", "la")           # Termina con
contains("Hola Mundo", "Mundo")   # Contiene
repeat("Hola", 3)                 # Repetir
pad_left("5", 3, "0")             # Rellenar izquierda
pad_right("5", 3, "0")            # Rellenar derecha
trim_left("  Hola")               # Recortar izquierda
trim_right("Hola  ")              # Recortar derecha
to_ascii("Hola")                  # A ASCII
from_ascii([72, 111, 108, 97])    # Desde ASCII
```

---

## regex

Expresiones regulares.

```mux
import regex

match("\\d+", "Tengo 25 años")                    # Buscar patrón
find_all("\\w+", "Hola mundo")                    # Todas las coincidencias
replace("\\d+", "XX", "Tengo 25 años")           # Reemplazar
split("\\s+", "Hola  mundo")                      # Dividir

# Validaciones
validate_email("usuario@example.com")
validate_url("https://www.example.com")
validate_phone("+34 123 456 789")

# Extracciones
extract_numbers("Tengo 25 años")
extract_emails("Contacta con ana@example.com")
```

---

## random

Generación de números aleatorios.

```mux
import random

randint(1, 100)              # Entero aleatorio
random()                     # Float entre 0 y 1
choice([1, 2, 3, 4, 5])     # Elemento aleatorio
shuffle([1, 2, 3, 4, 5])    # Mezclar lista
sample([1, 2, 3, 4, 5], 2)  # N elementos aleatorios
seed(42)                     # Establecer semilla
```

---

## database

Operaciones de base de datos.

```mux
import database

let db = connect("usuarios.db")
create_table("usuarios", ["id", "nombre", "email"])
insert("usuarios", {"nombre": "Ana", "email": "ana@example.com"})
let usuarios = select("usuarios", "edad >= 25")
update("usuarios", {"edad": 26}, "nombre = 'Ana'")
delete("usuarios", "nombre = 'Carlos'")
execute("SELECT * FROM usuarios")
close(db)
```

---

## filesystem

Manejo de archivos y directorios.

```mux
import filesystem

read("archivo.txt")                    # Leer archivo
write("archivo.txt", "contenido")      # Escribir
append("archivo.txt", "más texto")     # Agregar
exists("archivo.txt")                  # Verificar existencia
remove_file("archivo.txt")             # Eliminar
list_dir(".")                          # Listar directorio
create_dir("nueva_carpeta")            # Crear directorio
get_size("archivo.txt")                # Tamaño del archivo
```

---

## crypto

Criptografía y hashing.

```mux
import crypto

hash_md5("password")                   # Hash MD5
hash_sha256("password")                # Hash SHA256
encode_base64("Hola")                  # Codificar Base64
decode_base64("SGVsbG8=")              # Decodificar Base64
generate_uuid()                        # Generar UUID
encrypt("texto", "clave")              # Encriptar
decrypt("texto_encriptado", "clave")   # Desencriptar
```

---

## time

Manejo de tiempo y fechas.

```mux
import time

now()                    # Tiempo actual (timestamp)
sleep(2)                 # Dormir N segundos
format_date(1234567890)  # Formatear fecha
get_year()               # Año actual
get_month()              # Mes actual
get_day()                # Día actual
get_hour()               # Hora actual
get_minute()             # Minuto actual
get_second()             # Segundo actual
timestamp()              # Timestamp actual
measure_time(funcion)    # Medir tiempo de ejecución
```

---

## json

Trabajar con JSON.

```mux
import json

parse("{\"nombre\": \"Ana\"}")         # Parsear JSON
stringify({"nombre": "Ana"})           # A JSON string
load("datos.json")                     # Cargar desde archivo
save("datos.json", {"nombre": "Ana"})  # Guardar en archivo
pretty({"nombre": "Ana"})              # Formatear bonito
```

---

## console

Mejorar la consola.

```mux
import console

clear()                              # Limpiar consola
color("Texto", "red")                # Colorear texto
bold("Texto")                        # Negrita
italic("Texto")                      # Cursiva
underline("Texto")                   # Subrayado
progress_bar(50, 100)                # Barra de progreso
table([{"nombre": "Ana"}])           # Mostrar tabla
menu(["Opción 1", "Opción 2"])      # Mostrar menú
confirm("¿Continuar?")               # Confirmación
spinner("Cargando...")               # Spinner
```

---

## email

Envío de emails.

```mux
import email

configure_smtp("smtp.gmail.com", 587, "usuario", "password")
send("destinatario@example.com", "Asunto", "Mensaje")
send_html("destinatario@example.com", "Asunto", "<h1>HTML</h1>")
send_with_attachment("destinatario@example.com", "Asunto", "Mensaje", "archivo.pdf")
```

---

## 🎯 Ejemplos de Uso

### Aplicación Completa

```mux
import filesystem
import json
import console

# Leer configuración
let config = load("config.json")

# Procesar archivos
let archivos = list_dir(".")
each archivo in archivos
    if exists(archivo)
        let contenido = read(archivo)
        show("Procesando: " + archivo)
    end
end

# Guardar resultados
let resultados = {"procesados": len(archivos)}
save("resultados.json", resultados)

say("¡Proceso completado!")
```

### Bot con Base de Datos

```mux
import telegram_bot
import database

let bot = crear_bot("TOKEN")
let db = connect("bot.db")

create_table("usuarios", ["id", "nombre", "puntos"])

func registrar_handler(nombre)
    insert("usuarios", {"nombre": nombre, "puntos": 0})
    say("Usuario registrado: " + nombre)
end

comando(bot, "registrar", registrar_handler)
iniciar_bot(bot)
```

---

**Creado por MushhX** 🌍⚙️
