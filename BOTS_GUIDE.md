# Guía de Creación de Bots con Mux
**Creador: MushhX**

Esta guía te enseña cómo crear bots reales de Discord, Telegram y WhatsApp usando Mux.

## Bot de Discord

### 1. Obtener Token

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Crea una nueva aplicación
3. Ve a la sección "Bot"
4. Copia el token

### 2. Instalar Dependencias

```bash
pip install "mux-lang[discord]"
# o
pip install discord.py
```

### 3. Crear Bot en Mux

```mux
import discord_bot

let token = "TU_TOKEN_AQUI"
let bot = crear_bot(token)

func saludar_handler()
    print("¡Hola desde Discord!")
end

func info_handler()
    print("Bot creado con Mux")
end

comando(bot, "hola", saludar_handler)
comando(bot, "info", info_handler)

iniciar_bot(bot)
```

### 4. Ejecutar

```bash
mux mi_bot_discord.mux
```

## Bot de Telegram

### 1. Obtener Token

1. Habla con [@BotFather](https://t.me/botfather) en Telegram
2. Usa `/newbot` para crear un bot
3. Copia el token que te da

### 2. Instalar Dependencias

```bash
pip install "mux-lang[telegram]"
# o
pip install python-telegram-bot
```

### 3. Crear Bot en Mux

```mux
import telegram_bot

let token = "TU_TOKEN_AQUI"
let bot = crear_bot(token)

func start_handler()
    print("¡Bienvenido!")
end

func ayuda_handler()
    print("Comandos disponibles:")
    print("/start - Iniciar")
    print("/ayuda - Ver ayuda")
end

comando(bot, "start", start_handler)
comando(bot, "ayuda", ayuda_handler)

iniciar_bot(bot)
```

### 4. Ejecutar

```bash
mux mi_bot_telegram.mux
```

## Bot de WhatsApp (con Twilio)

### 1. Configurar Twilio

1. Crea cuenta en [Twilio](https://www.twilio.com/)
2. Obtén tu Account SID y Auth Token
3. Configura un número de WhatsApp

### 2. Instalar Dependencias

```bash
pip install "mux-lang[whatsapp]"
# o
pip install twilio
```

### 3. Crear Bot en Mux

```mux
import whatsapp_bot

let account_sid = "TU_ACCOUNT_SID"
let auth_token = "TU_AUTH_TOKEN"
let numero = "+1234567890"

let bot = crear_bot(account_sid, auth_token, numero)

func mensaje_handler(texto)
    print("Mensaje recibido: " + texto)
    return "¡Hola desde Mux!"
end

mensaje(bot, mensaje_handler)

iniciar_bot(bot)
```

## Características Avanzadas

### Comandos con Parámetros

```mux
func saludar_handler(nombre)
    print("¡Hola, " + nombre + "!")
end

comando_con_params(bot, "saludar", saludar_handler)
```

### Respuestas Dinámicas

```mux
func calcular_handler(operacion)
    let partes = operacion.split(" ")
    let a = int(partes[0])
    let b = int(partes[2])
    let op = partes[1]
    
    if op == "+"
        return str(a + b)
    elif op == "-"
        return str(a - b)
    elif op == "*"
        return str(a * b)
    elif op == "/"
        return str(a / b)
    end
    
    return "Operación no válida"
end

comando(bot, "calc", calcular_handler)
```

### Almacenar Datos

```mux
let usuarios = {}

func registrar_handler(nombre)
    usuarios[nombre] = {"puntos": 0}
    print("Usuario " + nombre + " registrado")
end

func puntos_handler(nombre)
    if nombre in usuarios
        let puntos = usuarios[nombre]["puntos"]
        print(nombre + " tiene " + str(puntos) + " puntos")
    else
        print("Usuario no encontrado")
    end
end

comando(bot, "registrar", registrar_handler)
comando(bot, "puntos", puntos_handler)
```

## Despliegue

### Ejecutar en Servidor

```bash
# En servidor Linux
nohup mux mi_bot.mux &

# Con screen
screen -S bot
mux mi_bot.mux
# Ctrl+A, D para detach
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -e ".[full]"

CMD ["mux", "mi_bot.mux"]
```

```bash
docker build -t mi-bot-mux .
docker run -d mi-bot-mux
```

### Heroku

```bash
# Crear Procfile
echo "worker: mux mi_bot.mux" > Procfile

# Desplegar
heroku create mi-bot-mux
git push heroku main
heroku ps:scale worker=1
```

## Mejores Prácticas

### 1. Seguridad

```mux
# NO hagas esto:
let token = "123456789:ABC..."

# Haz esto:
let token = input("Token: ")
# O usa variables de entorno
```

### 2. Manejo de Errores

```mux
func comando_handler(params)
    if len(params) == 0
        return "❌ Faltan parámetros"
    end
    
    # Tu lógica aquí
    return "✅ Comando ejecutado"
end
```

### 3. Logging

```mux
func log(mensaje)
    print("[" + str(time()) + "] " + mensaje)
end

func comando_handler()
    log("Comando ejecutado")
end
```

### 4. Rate Limiting

```mux
let ultimo_uso = {}

func puede_usar(usuario)
    let ahora = time()
    if usuario in ultimo_uso
        let diff = ahora - ultimo_uso[usuario]
        if diff < 5
            return false
        end
    end
    ultimo_uso[usuario] = ahora
    return true
end
```

## Recursos

- [Discord.py Docs](https://discordpy.readthedocs.io/)
- [python-telegram-bot Docs](https://python-telegram-bot.readthedocs.io/)
- [Twilio Docs](https://www.twilio.com/docs)

## Soporte

Si tienes problemas creando bots, abre un issue en GitHub.

---

**¡Crea bots increíbles con Mux!** 🤖

Creado por MushhX 🌍⚙️
