# Mux

Mux es un lenguaje pequeño interpretado en Python. Incluye un parser con posiciones de error, funciones, colecciones, control de flujo, módulos nativos y una CLI.

## Instalar

Requiere Python 3.8 o posterior.

```console
python -m pip install .
mux --version
mux examples/hola_mundo.mux
```

Las integraciones externas se instalan solo si se necesitan:

```console
python -m pip install ".[web,discord,telegram,whatsapp,crypto]"
```

## Primer programa

```mux
func saludar(nombre)
    return "Hola, " + nombre
end

let nombre = ask("¿Cómo te llamas?")
print(saludar(nombre))
```

Mux admite variables `let`, números, strings, booleanos y `null`; listas y diccionarios; funciones con retorno; condicionales; `repeat`, `N times`, `while`, `for`, `each`, `until` y `loop`; y `break`/`continue` dentro de bucles. Las expresiones lógicas usan `&&`, `||` y `!`. Las instrucciones se separan por saltos de línea y los bloques terminan con `end`.

## CLI

```console
mux programa.mux             # Ejecuta un archivo
mux --check programa.mux      # Comprueba la sintaxis
mux --tokens programa.mux     # Muestra tokens con línea y columna
mux --ast programa.mux        # Muestra el árbol sintáctico
mux --max-steps 10000 programa.mux
mux --repl                    # Abre el REPL
type programa.mux | mux -      # Lee el programa desde stdin en Windows
```

Los errores muestran archivo, línea y columna. El límite de pasos es opcional y ayuda a detener bucles que no terminan.

## Módulos estándar

Los módulos estándar son implementaciones nativas del intérprete; no devuelven datos simulados. Incluyen `math`, `random`, `http`, `filesystem`, `json`, `crypto`, `regex`, `strings`, `time`, `database` (SQLite), `email` (SMTP), `console`, `env`, `web` (Flask), `discord_bot`, `telegram_bot` y `whatsapp` (Twilio). Flask, los SDK de bots, Twilio y `cryptography` son dependencias opcionales. Consulta [STDLIB_REFERENCE.md](STDLIB_REFERENCE.md) para firmas, límites y configuración.

## Paquetes Mux

`mux-pkg` instala módulos desde una carpeta, un archivo `.mux`, un ZIP local o una URL HTTPS con nombre y hash SHA-256 explícitos:

```console
mux-pkg install ./mi_paquete --name saludos
mux-pkg install https://example.org/saludos.zip --name saludos --sha256 HASH_SHA256
mux-pkg list
mux-pkg remove saludos
```

Un paquete puede incluir `mux-package.json` con `name`, `version`, `description` y `main`. Sin manifiesto, debe contener un único archivo `.mux`. Los paquetes se guardan en el directorio de datos del usuario; `MUX_HOME` permite elegir otro. No hay un registro remoto público configurado.

## Crear ejecutables

```console
python -m pip install ".[build]"
python build_exe.py
```

`build_exe.py` genera un ejecutable para el sistema operativo actual en `dist/`. En Windows, `python build_installer.py` crea un instalador si Inno Setup está instalado. `python create_portable_installer.py` genera un ZIP portable. El tamaño y los formatos dependen de la plataforma y del entorno de compilación.

## Desarrollo

- [Inicio rápido](QUICKSTART.md)
- [Características](FEATURES.md)
- [Referencia de módulos](STDLIB_REFERENCE.md)
- [Comandos del lenguaje](UNIQUE_COMMANDS.md)
- [Guía de bots](BOTS_GUIDE.md)
- [Guía de distribución](DISTRIBUTION.md)
- [Plan de desarrollo](ROADMAP.md)
- [Contribuir](CONTRIBUTING.md)

Licencia MIT; consulta [LICENSE](LICENSE).
