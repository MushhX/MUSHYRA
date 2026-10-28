# MUSHYRA

MUSHYRA es un lenguaje interpretado. Sus programas se guardan como archivos `.myr` y se ejecutan con el comando `myr`. Incluye posiciones de origen, funciones, colecciones, módulos nativos y herramientas de desarrollo.

## Instalar

Requiere Python 3.8 o posterior.

```console
python -m pip install .
myr --version
myr examples/hola_mundo.myr
```

Las integraciones externas se instalan solo si se necesitan:

```console
python -m pip install ".[web,discord,telegram,whatsapp,crypto,regex]"
```

## Primer programa

```myr
func saludar(nombre)
    return "Hola, " + nombre
end

let nombre = ask("¿Cómo te llamas?")
print(saludar(nombre))
```

MUSHYRA admite variables `let`, números, strings, booleanos y `null`; listas y diccionarios; funciones con retorno; condicionales y `match`/`case`; excepciones propias con `throw`, `catch` y `finally`; `repeat`, `N times`, `while`, `for`, `each`, `until` y `loop`; y `break`/`continue` dentro de bucles. Las expresiones lógicas usan `&&`, `||` y `!`. Las instrucciones se separan por saltos de línea y los bloques terminan con `end`.

## CLI

```console
myr programa.myr              # Ejecuta un archivo
myr --check programa.myr       # Comprueba la sintaxis
myr --lint programa.myr        # Diagnósticos estáticos
myr --format programa.myr      # Formatea y muestra el resultado
myr --write-format programa.myr # Formatea el archivo
myr --watch programa.myr       # Reejecuta al cambiar el archivo
myr --tokens programa.myr      # Muestra tokens con línea y columna
myr --ast programa.myr         # Muestra el árbol sintáctico
myr --max-steps 10000 programa.myr
myr programa.myr -- argumento  # Pasa argumentos al programa como args
myr --repl                     # Abre el REPL
type programa.myr | myr -       # Lee el programa desde stdin en Windows
```

Los errores muestran archivo, línea y columna, y las trazas incluyen ubicación de llamada y definición. El resolver valida ámbitos antes de ejecutar; el depurador `--debugger` ofrece paso, breakpoints, variables y pila. Presupuestos de pasos, salida, asignaciones estimadas y tiempo ayudan a contener programas accidentales. `--sandbox` restringe módulos y capacidades; no sustituye aislamiento del sistema operativo.

Para usar diagnósticos y navegación en VS Code, instala MUSHYRA y abre `editors/vscode` como extensión de desarrollo. El servidor integrado se inicia con `myr --lsp`; no requiere dependencias de terceros.

Empieza una aplicación con `myr init mi-proyecto --template app` o una biblioteca con `myr init mi-biblioteca --template library`; ejecuta el ejemplo con `myr mi-proyecto/main.myr`.

El ejemplo `examples/exceptions.myr` muestra cómo lanzar un valor, filtrarlo con patrones y guardas `catch`, y ejecutar `finally` al salir de una función.

Consulta [CONFIGURATION.md](CONFIGURATION.md) para las claves y prioridades.

Los códigos de error y sus categorías están en [DIAGNOSTICS.md](DIAGNOSTICS.md).

## Módulos estándar

Los módulos estándar son implementaciones nativas del intérprete; no devuelven datos simulados. Incluyen `math`, `random`, `sequence`, `path`, `csv`, `toml`, `http`, `filesystem`, `json`, `crypto`, `regex`, `strings`, `time`, `database` (SQLite), `email` (SMTP), `console`, `env`, `web` (Flask), `discord_bot`, `telegram_bot` y `whatsapp` (Twilio). Flask, los SDK de bots, Twilio, `tomli` para Python anterior a 3.11 y `cryptography` son dependencias opcionales. Consulta [STDLIB_REFERENCE.md](STDLIB_REFERENCE.md) para firmas, límites y configuración.

## Paquetes MUSHYRA

`myr-pkg` instala módulos desde una carpeta, un archivo `.myr`, un ZIP local o una URL HTTPS con nombre y hash SHA-256 explícitos:

```console
myr-pkg install ./mi_paquete --name saludos
myr-pkg install https://example.org/saludos.zip --name saludos --sha256 HASH_SHA256
myr-pkg install saludos --from-registry --registry https://example.org/index.json --trust-store claves.json
myr-pkg lock
myr-pkg install-lock
myr-pkg verify
myr-pkg list
myr-pkg remove saludos
```

Un paquete puede incluir `myr-package.json` con `name`, `version`, `description`, `main`, `dependencies` y `files`. Para paquetes remotos se verifican SHA-256 y firmas Ed25519; consulta [PACKAGE_REGISTRY.md](PACKAGE_REGISTRY.md) para preparar un manifiesto y un índice. El cliente admite un registro local o HTTPS, pero el proyecto no aloja uno. Los paquetes se guardan en el directorio de datos del usuario; configura `MYR_HOME` para elegir otro.

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
- [Especificación del lenguaje](LANGUAGE_SPEC.md)
- [Protocolo del registro de paquetes](PACKAGE_REGISTRY.md)
- [Modelo de seguridad](SECURITY.md)
- [Configuración de la CLI](CONFIGURATION.md)
- [Soporte de VS Code](editors/vscode/README.md)
- [Cambios por versión](CHANGELOG.md)
- [Comandos del lenguaje](UNIQUE_COMMANDS.md)
- [Guía de bots](BOTS_GUIDE.md)
- [Guía de distribución](DISTRIBUTION.md)
- [Plan de desarrollo](ROADMAP.md)
- [Contribuir](CONTRIBUTING.md)

Licencia MIT; consulta [LICENSE](LICENSE).
