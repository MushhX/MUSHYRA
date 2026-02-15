# Mux Programming Language 🌍⚙️

Un lenguaje de programación moderno, accesible y ligero diseñado para que cualquiera pueda aprenderlo en horas y usarlo en proyectos reales en días.

**Creador: MushhX**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/mushhx/mux)

## 🎯 Filosofía

Mux busca ser una puerta de entrada global a la programación sin fricción, priorizando:
- **Claridad** sobre complejidad
- **Rapidez** de aprendizaje
- **Experiencia limpia** de desarrollo

## ✨ Características

✨ **Sintaxis Limpia**: Sin símbolos innecesarios, código legible y natural  
🚀 **Rápido de Aprender**: Domínalo en horas, úsalo en días  
🌐 **Multiplataforma**: Funciona en Windows, Linux y macOS  
📦 **Sistema de Paquetes**: Gestor integrado para módulos  
🤖 **Bots**: Crea bots de Discord, Telegram, WhatsApp  
🌍 **Desarrollo Web**: Aplicaciones web con sintaxis simple  
📚 **Librería Estándar**: Matemáticas, HTTP, y más  
💾 **Compilable**: Convierte tus programas a .exe  

## 🚀 Inicio Rápido

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/mushhx/mux.git
cd mux

# Instalar
pip install -e .

# Verificar
mux --version
```

### Tu Primer Programa

```mux
# hola.mux
print("¡Hola, Mundo!")

let nombre = input("¿Cómo te llamas? ")
print("¡Hola, " + nombre + "!")
```

```bash
mux hola.mux
```

## 📖 Sintaxis

### Variables y Tipos
```mux
let nombre = "Ana"
let edad = 25
let activo = true
let numeros = [1, 2, 3, 4, 5]
let datos = {"nombre": "Ana", "edad": 25}
```

### Condicionales
```mux
if edad >= 18
    print("Eres mayor de edad")
elif edad >= 13
    print("Eres adolescente")
else
    print("Eres niño")
end
```

### Bucles
```mux
# Repeat
repeat 5
    print("Iteración")
end

# While
while edad < 30
    edad = edad + 1
end

# For
for num in numeros
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
    return "Saludado"
end

func sumar(a, b)
    return a + b
end

saludar("Mux")
let resultado = sumar(10, 20)
```

### Listas y Métodos
```mux
let frutas = ["manzana", "banana"]
frutas.append("naranja")
print(frutas[0])

let texto = "Hola Mundo"
print(texto.upper())
print(texto.split(" "))
```

### Importar Módulos
```mux
import math
print(sqrt(16))  # 4.0
print(pi)        # 3.14159...
```

## 🤖 Crear Bots

### Bot de Discord
```mux
import discord_bot

let bot = crear_bot("TU_TOKEN")

func saludar_handler()
    print("¡Hola desde Discord!")
end

comando(bot, "hola", saludar_handler)
iniciar_bot(bot)
```

### Bot de Telegram
```mux
import telegram_bot

let bot = crear_bot("TU_TOKEN")
comando(bot, "start", start_handler)
iniciar_bot(bot)
```

Ver [BOTS_GUIDE.md](BOTS_GUIDE.md) para guía completa.

## 🌐 Desarrollo Web

```mux
import web

let app = crear_app()

func index_handler()
    return "<h1>¡Hola desde Mux!</h1>"
end

ruta(app, "/", index_handler)
iniciar(app, 5000)
```

## 📦 Gestor de Paquetes

```bash
# Listar paquetes
mux-pkg list

# Instalar paquete
mux-pkg install nombre_paquete

# Desinstalar paquete
mux-pkg remove nombre_paquete
```

## 💾 Compilar a Ejecutable

```bash
# Instalar PyInstaller
pip install pyinstaller

# Compilar
python build_exe.py

# Usar ejecutable
./dist/mux examples/hola_mundo.mux
```

## 📚 Ejemplos

La carpeta `examples/` contiene 14 ejemplos completos:

**Básicos:**
- `hola_mundo.mux` - Primer programa
- `variables.mux` - Variables y tipos
- `condicionales.mux` - If/elif/else
- `bucles.mux` - Repeat, while, for
- `funciones.mux` - Definir funciones

**Estructuras de Datos:**
- `listas_y_diccionarios.mux` - Listas y diccionarios

**Aplicaciones:**
- `calculadora.mux` - Calculadora completa
- `fibonacci.mux` - Secuencia Fibonacci
- `matematicas.mux` - Librería math
- `todo_list.mux` - Lista de tareas interactiva
- `juego_adivinanza.mux` - Juego interactivo

**Bots y Web:**
- `bot_discord.mux` - Bot de Discord
- `bot_telegram.mux` - Bot de Telegram
- `web_app.mux` - Aplicación web

```bash
# Ejecutar ejemplos
mux examples/hola_mundo.mux
mux examples/calculadora.mux
mux examples/fibonacci.mux
```

## 🛠️ Funciones Builtin

- `print(valor)` - Imprimir en consola
- `input(prompt)` - Leer entrada del usuario
- `len(objeto)` - Longitud de lista/string
- `type(valor)` - Tipo de dato
- `str(valor)` - Convertir a string
- `int(valor)` - Convertir a entero
- `float(valor)` - Convertir a decimal
- `range(start, stop, step)` - Generar rango

## 📚 Librería Estándar

Mux incluye 15 módulos en su librería estándar:

- **math** - Funciones matemáticas (abs, max, min, pow, sqrt, pi, e)
- **http** - Peticiones HTTP (get, post)
- **web** - Aplicaciones web con Flask
- **discord_bot** - Bots de Discord
- **telegram_bot** - Bots de Telegram
- **strings** - Manipulación avanzada de strings
- **regex** - Expresiones regulares y validaciones
- **random** - Números aleatorios
- **database** - Operaciones de base de datos
- **filesystem** - Manejo de archivos y directorios
- **crypto** - Criptografía y hashing
- **time** - Tiempo y fechas
- **json** - Trabajar con JSON
- **console** - Consola mejorada con colores
- **email** - Envío de emails

Ver [STDLIB_REFERENCE.md](STDLIB_REFERENCE.md) para documentación completa.

## 🎯 Comandos Únicos

Mux incluye comandos únicos que hacen la programación más expresiva:

- **show()** - Mostrar con emoji 👁️
- **say()** - Decir con emoji 💬
- **ask()** - Preguntar con emoji ❓
- **wait()** - Esperar con emoji ⏳
- **assert()** - Verificar condiciones
- **unless** - Si no (inverso de if)
- **until** - Hasta que (inverso de while)
- **each** - Iterar (alias de for)
- **loop** - Bucle infinito
- **pass** - No hacer nada
- **exit()** - Salir del programa

Ver [UNIQUE_COMMANDS.md](UNIQUE_COMMANDS.md) para documentación completa.

## 📖 Documentación

- [QUICKSTART.md](QUICKSTART.md) - Inicio rápido en 5 minutos
- [INSTALL.md](INSTALL.md) - Guía de instalación detallada
- [FEATURES.md](FEATURES.md) - Lista completa de características
- [STDLIB_REFERENCE.md](STDLIB_REFERENCE.md) - Referencia de librería estándar
- [UNIQUE_COMMANDS.md](UNIQUE_COMMANDS.md) - Comandos únicos de Mux
- [BOTS_GUIDE.md](BOTS_GUIDE.md) - Guía para crear bots
- [ROADMAP.md](ROADMAP.md) - Plan de desarrollo
- [CONTRIBUTING.md](CONTRIBUTING.md) - Guía de contribución
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Resumen del proyecto
- [COMMANDS.md](COMMANDS.md) - Comandos útiles de terminal

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Lee [CONTRIBUTING.md](CONTRIBUTING.md) para empezar.

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/mi-feature`
3. Commit: `git commit -m 'Añadir feature'`
4. Push: `git push origin feature/mi-feature`
5. Abre un Pull Request

## 🗺️ Roadmap

### Versión Actual: 1.0.0 ✅
- ✅ Intérprete completo funcional
- ✅ Listas, diccionarios, funciones
- ✅ Sistema de módulos
- ✅ Librería estándar
- ✅ CLI y gestor de paquetes
- ✅ Compilación a .exe
- ✅ 14 ejemplos completos
- ✅ Documentación completa

### Próxima Versión: 1.1.0 🚧
- [ ] REPL interactivo
- [ ] Manejo de archivos
- [ ] Try/catch
- [ ] Clases y objetos
- [ ] Comprensión de listas

Ver [ROADMAP.md](ROADMAP.md) para más detalles.

## 📊 Estadísticas

- **Líneas de código**: 3000+
- **Ejemplos**: 20+
- **Módulos stdlib**: 15
- **Comandos únicos**: 11
- **Características**: 70+
- **Documentación**: 12 archivos

## 🎓 Casos de Uso

- **Educación**: Enseñar programación a principiantes
- **Automatización**: Scripts y tareas repetitivas
- **Bots**: Discord, Telegram, WhatsApp
- **Web**: Aplicaciones web pequeñas y medianas
- **Prototipado**: Probar ideas rápidamente
- **Embebidos**: Sistemas con recursos limitados

## 📝 Licencia

MIT License - Ver [LICENSE](LICENSE)

## 👨‍💻 Creador

**MushhX**

Mux es un proyecto de código abierto creado con ❤️ para hacer la programación más accesible para todos.

## 🌟 Filosofía

> "La claridad sobre la complejidad. La rapidez sobre la perfección. La experiencia sobre las características."

Mux no busca ser el lenguaje más rápido o con más características. Busca ser el lenguaje más claro, más fácil de aprender y más agradable de usar.

## 🔗 Enlaces

- **Repositorio**: [https://github.com/MushhX/Mux](https://github.com/MushhX/Mux)
- **Documentación**: Ver archivos .md en el repositorio
- **Ejemplos**: Carpeta `examples/`
- **Issues**: [https://github.com/MushhX/Mux/issues](https://github.com/MushhX/Mux/issues)

## 💬 Comunidad

¿Tienes preguntas? ¿Quieres compartir tu proyecto en Mux?

- Abre un issue en GitHub
- Comparte tus proyectos
- Contribuye al código
- Mejora la documentación

---

**Mux: Una pequeña nación digital** 🌍⚙️

**Creado con ❤️ por MushhX**
