# Inicio rápido

## Instalación

Desde la raíz del repositorio:

```console
python -m pip install .
myr --version
myr examples/hola_mundo.myr
```

Requiere Python 3.8 o posterior. Para instalar en modo editable durante el desarrollo, usa `python -m pip install -e .`.

## Primer programa

Guarda lo siguiente como `hola.myr`:

```myr
let nombre = ask("¿Cómo te llamas?")
print("Hola, " + nombre)
```

Y ejecútalo con `myr hola.myr`.

## Sintaxis básica

```myr
let total = 0
for numero in range(1, 6)
    total = total + numero
end

if total == 15
    print("La suma es " + str(total))
else
    print("Algo ha fallado")
end

func duplicar(valor)
    return valor * 2
end

print(duplicar(total))
```

También existen `repeat N`, `N times do`, `while`, `each`, `until`, `unless`, `loop`, `break` y `continue`. Cada instrucción ocupa su línea; los bloques terminan con `end`.

## Colecciones y módulos

```myr
let persona = {"nombre": "Ana", "edad": 25}
persona["edad"] = 26
let numeros = [1, 2, 3]
numeros.append(4)

import math as m
print(m.sqrt(16))
```

Consulta [STDLIB_REFERENCE.md](STDLIB_REFERENCE.md) para los módulos, funciones y extras opcionales.

## CLI

```console
myr --check hola.myr
myr --tokens hola.myr
myr --ast hola.myr
myr --lint hola.myr
myr --format hola.myr
myr --max-steps 10000 hola.myr
myr --repl
```

Para leer el programa desde la entrada estándar, usa `myr -`.

## Paquetes MUSHYRA

El gestor instala paquetes locales o paquetes de un índice que tú configures:

```console
myr-pkg install ./saludos --name saludos
myr-pkg list
myr-pkg remove saludos
```

Las descargas HTTPS requieren `--sha256 HASH` y, salvo que se pida expresamente `--allow-unsigned`, una firma Ed25519 de una clave confiable. Puedes configurar `MYR_PACKAGE_REGISTRY` para buscar e instalar desde un índice firmado y `MYR_PACKAGE_TRUST_STORE` para establecer el trust store predeterminado. Consulta [PACKAGE_REGISTRY.md](PACKAGE_REGISTRY.md). El manifiesto opcional se llama `mux-package.json` por compatibilidad; su propiedad `main` debe apuntar a un archivo `.myr` del paquete.

## Compilar

```console
python -m pip install ".[build]"
python build_exe.py
```

La compilación usa PyInstaller para el sistema operativo actual. En Windows, `python build_installer.py` genera un instalador si Inno Setup está instalado.
