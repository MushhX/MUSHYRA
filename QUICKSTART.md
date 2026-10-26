# Inicio rápido

## Instalación

Desde la raíz del repositorio:

```console
python -m pip install .
mux --version
mux examples/hola_mundo.mux
```

Requiere Python 3.8 o posterior. Para instalar en modo editable durante el desarrollo, usa `python -m pip install -e .`.

## Primer programa

Guarda lo siguiente como `hola.mux`:

```mux
let nombre = ask("¿Cómo te llamas?")
print("Hola, " + nombre)
```

Y ejecútalo con `mux hola.mux`.

## Sintaxis básica

```mux
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

```mux
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
mux --check hola.mux
mux --tokens hola.mux
mux --ast hola.mux
mux --max-steps 10000 hola.mux
mux --repl
```

Para leer el programa desde la entrada estándar, usa `mux -`.

## Paquetes Mux

El gestor instala paquetes locales o archivos ZIP HTTPS verificados:

```console
mux-pkg install ./saludos --name saludos
mux-pkg list
mux-pkg remove saludos
```

Las descargas HTTPS también requieren `--sha256 HASH` y `--name nombre`. No hay un registro remoto configurado. El manifiesto opcional se llama `mux-package.json`; su propiedad `main` debe apuntar a un archivo `.mux` del paquete.

## Compilar

```console
python -m pip install ".[build]"
python build_exe.py
```

La compilación usa PyInstaller para el sistema operativo actual. En Windows, `python build_installer.py` genera un instalador si Inno Setup está instalado.
