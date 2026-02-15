# Inicio Rápido con Mux
**Creador: MushhX**

## Instalación en 30 segundos

```bash
# Clonar repositorio
git clone https://github.com/MushhX/Mux.git
cd mux

# Instalar
pip install -e .

# Probar
mux examples/hola_mundo.mux
```

## Tu Primer Programa

Crea un archivo `hola.mux`:

```mux
print("¡Hola, Mundo!")

let nombre = input("¿Cómo te llamas? ")
print("¡Hola, " + nombre + "!")
```

Ejecuta:
```bash
mux hola.mux
```

## Ejemplos Rápidos

### Variables y Operaciones
```mux
let edad = 25
let nombre = "Ana"
let activo = true

let suma = 10 + 5
let resultado = suma * 2
print(resultado)  # 30
```

### Condicionales
```mux
let edad = 18

if edad >= 18
    print("Mayor de edad")
elif edad >= 13
    print("Adolescente")
else
    print("Niño")
end
```

### Bucles
```mux
# Repeat
repeat 5
    print("Hola")
end

# While
let i = 0
while i < 5
    print(i)
    i = i + 1
end

# For
for num in [1, 2, 3, 4, 5]
    print(num)
end

for i in range(10)
    print(i)
end
```

### Funciones
```mux
func saludar(nombre)
    print("Hola, " + nombre)
end

func sumar(a, b)
    return a + b
end

saludar("Mux")
let resultado = sumar(10, 20)
print(resultado)  # 30
```

### Listas
```mux
let numeros = [1, 2, 3, 4, 5]
print(numeros[0])  # 1

numeros.append(6)
print(numeros)  # [1, 2, 3, 4, 5, 6]

for num in numeros
    print(num)
end
```

### Diccionarios
```mux
let persona = {
    "nombre": "Ana",
    "edad": 25,
    "ciudad": "Madrid"
}

print(persona["nombre"])  # Ana
persona["edad"] = 26
```

### Importar Módulos
```mux
import math

print(pi)  # 3.14159...
print(sqrt(16))  # 4.0
print(pow(2, 8))  # 256
```

## Ejemplos Incluidos

Explora la carpeta `examples/`:

```bash
# Básicos
mux examples/hola_mundo.mux
mux examples/variables.mux
mux examples/condicionales.mux
mux examples/bucles.mux
mux examples/funciones.mux

# Estructuras de datos
mux examples/listas_y_diccionarios.mux

# Aplicaciones
mux examples/calculadora.mux
mux examples/fibonacci.mux
mux examples/matematicas.mux

# Interactivos (requieren input)
mux examples/todo_list.mux
mux examples/juego_adivinanza.mux

# Bots (requieren configuración)
mux examples/bot_discord.mux
mux examples/bot_telegram.mux
mux examples/web_app.mux
```

## Crear un Ejecutable

```bash
# Instalar PyInstaller
pip install pyinstaller

# Compilar
python build_exe.py

# Usar ejecutable
./dist/mux examples/hola_mundo.mux
```

## Gestor de Paquetes

```bash
# Listar paquetes
mux-pkg list

# Instalar paquete
mux-pkg install nombre_paquete

# Desinstalar
mux-pkg remove nombre_paquete
```

## Próximos Pasos

1. Lee [README.md](README.md) para documentación completa
2. Explora [FEATURES.md](FEATURES.md) para ver todas las características
3. Revisa [ROADMAP.md](ROADMAP.md) para ver el futuro de Mux
4. Contribuye siguiendo [CONTRIBUTING.md](CONTRIBUTING.md)

## Ayuda

```bash
mux --help
mux --version
```

## Recursos

- Documentación: [README.md](README.md)
- Ejemplos: `examples/`
- Librería estándar: `mux_lang/stdlib/`

---

**¡Empieza a programar con Mux ahora!** 🚀

Creado por MushhX 🌍⚙️
