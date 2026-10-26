# Bots e integraciones externas

Los módulos conectan con servicios reales. Instala el extra correspondiente y guarda los tokens en variables de entorno; no los escribas en el archivo `.myr` ni los subas al repositorio.

Desde el checkout, por ejemplo:

```console
python -m pip install ".[discord,telegram,whatsapp]"
```

## Discord

Crea una aplicación y un bot en el [portal de desarrolladores de Discord](https://discord.com/developers/applications), y configura la variable `MYR_DISCORD_TOKEN`.

```myr
import env
import discord_bot

let bot = discord_bot.crear_bot(env.require("MYR_DISCORD_TOKEN"))

func saludar()
    return "¡Hola desde MUSHYRA!"
end

discord_bot.comando(bot, "hola", saludar)
discord_bot.iniciar_bot(bot)
```

Los comandos usan el prefijo `!`. El handler no recibe argumentos; su valor de retorno se envía al canal. Para comandos por prefijo, habilita el intent de contenido de mensajes en la configuración del bot de Discord.

## Telegram

Crea un bot con [BotFather](https://t.me/BotFather) y define `MYR_TELEGRAM_TOKEN`.

```myr
import env
import telegram_bot

let bot = telegram_bot.crear_bot(env.require("MYR_TELEGRAM_TOKEN"))

func iniciar()
    return "¡Bienvenido!"
end

telegram_bot.comando(bot, "start", iniciar)
telegram_bot.iniciar_bot(bot)
```

El nombre del comando se pasa sin `/`. El handler no recibe argumentos y su valor de retorno se responde al mensaje.

## WhatsApp saliente con Twilio

Configura las credenciales `MYR_TWILIO_ACCOUNT_SID` y `MYR_TWILIO_AUTH_TOKEN`; `MYR_TWILIO_WHATSAPP_FROM` puede elegir el remitente. Después instala el extra `whatsapp` y ejecuta:

```myr
import env
import whatsapp

let destino = env.require("MYR_WHATSAPP_TO")
let resultado = whatsapp.send(destino, "Mensaje enviado desde MUSHYRA")
print(resultado["status"])
```

Este módulo envía mensajes mediante Twilio; no recibe mensajes entrantes ni configura webhooks. El número destinatario debe estar habilitado en la cuenta y el entorno de Twilio.

## Ejecución y secretos

En PowerShell, define una variable para la sesión con `$env:MYR_DISCORD_TOKEN = "..."`; en macOS/Linux usa `export MYR_DISCORD_TOKEN="..."`. Luego ejecuta `myr mi_bot.myr` en esa misma terminal.

No publiques tokens, contraseñas, datos personales ni logs que los contengan. Revoca y rota cualquier credencial que se haya compartido por error. Los servicios aplican sus propios límites de uso y condiciones.
