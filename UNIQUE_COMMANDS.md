# Comandos Únicos de Mux
**Creador: MushhX**

Mux incluye comandos únicos que hacen la programación más expresiva y natural.

## 📋 Índice

1. [show](#show) - Mostrar con emoji
2. [say](#say) - Decir con emoji
3. [ask](#ask) - Preguntar con emoji
4. [wait](#wait) - Esperar con emoji
5. [assert](#assert) - Verificar condiciones
6. [unless](#unless) - Si no (inverso de if)
7. [until](#until) - Hasta que (inverso de while)
8. [each](#each) - Iterar (alias de for)
9. [loop](#loop) - Bucle infinito
10. [pass](#pass) - No hacer nada
11. [exit](#exit) - Salir del programa

---

## show

Mostrar un valor con emoji 👁️

```mux
show("Hola Mundo")
# 👁️ Hola Mundo

let edad = 25
show(edad)
# 👁️ 25

let lista = [1, 2, 3]
show(lista)
# 👁️ [1, 2, 3]
```

**Diferencia con print:**
- `print()` - Salida estándar
- `show()` - Salida con emoji visual

---

## say

Decir un mensaje con emoji 💬

```mux
say("¡Hola!")
# 💬 ¡Hola!

say("Proceso completado")
# 💬 Proceso completado
```

**Uso recomendado:**
- Mensajes importantes
- Notificaciones al usuario
- Feedback de operaciones

---

## ask

Preguntar al usuario con emoji ❓

```mux
let nombre = ask("¿Cómo te llamas?")
# ❓ ¿Cómo te llamas? _

let edad = ask("¿Cuántos años tienes?")
let edad_num = int(edad)
```

**Diferencia con input:**
- `input()` - Entrada estándar
- `ask()` - Entrada con emoji de pregunta

---

## wait

Esperar N segundos; informa antes de pausar con el emoji ⏳.

```mux
say("Iniciando proceso...")
wait(2)
say("Proceso completado")

# ⏳ Esperando 2 segundos...
```

**Uso recomendado:**
- Pausas entre operaciones
- Delays en bots
- Simulaciones

---

## assert

Verificar condiciones con mensajes claros

```mux
let edad = 25
assert(edad >= 18, "Debe ser mayor de edad")
# ✓ Pasa

let edad = 15
assert(edad >= 18, "Debe ser mayor de edad")
# ❌ Assert: Debe ser mayor de edad
```

**Uso recomendado:**
- Validaciones
- Precondiciones
- Testing

---

## unless

Ejecutar código si la condición es FALSA (inverso de if)

```mux
let llueve = false
unless llueve
    say("¡Vamos al parque!")
end
# 💬 ¡Vamos al parque!

let llueve = true
unless llueve
    say("¡Vamos al parque!")
end
# (no se ejecuta)
```

**Equivalente:**
```mux
# unless condicion
if !condicion
```

---

## until

Repetir hasta que la condición sea VERDADERA (inverso de while)

```mux
let contador = 0
until contador >= 5
    show(contador)
    contador = contador + 1
end
# 👁️ 0
# 👁️ 1
# 👁️ 2
# 👁️ 3
# 👁️ 4
```

**Equivalente:**
```mux
# until condicion
while !condicion
```

---

## each

Iterar sobre elementos (alias más natural de for)

```mux
let frutas = ["manzana", "banana", "naranja"]
each fruta in frutas
    say("Me gusta la " + fruta)
end
# 💬 Me gusta la manzana
# 💬 Me gusta la banana
# 💬 Me gusta la naranja
```

**Equivalente:**
```mux
# each item in lista
for item in lista
```

---

## loop

Bucle infinito (hasta break)

```mux
let contador = 0
loop
    show(contador)
    contador = contador + 1
    
    if contador >= 5
        break
    end
end
```

**Uso recomendado:**
- Servidores
- Bots
- Procesos continuos

---

## pass

No ejecutar ninguna acción y continuar con la siguiente instrucción.

```mux
let x = 10
if x > 5
    pass  # No-op mientras no haya lógica que ejecutar
end

func procesar_datos()
    pass
end
```

**Uso recomendado:**
- Código en desarrollo
- Placeholders
- Estructuras vacías

---

## exit

Salir del programa con código de salida

```mux
exit()        # Salir con código 0
exit(0)       # Salir con código 0 (éxito)
exit(1)       # Salir con código 1 (error)

# Ejemplo
let edad = 15
if edad < 18
    say("Debes ser mayor de edad")
    exit(1)
end
```

---

## 🎯 Ejemplos Combinados

### Validación de Entrada

```mux
let edad = ask("¿Cuántos años tienes?")
let edad_num = int(edad)

assert(edad_num >= 0, "La edad no puede ser negativa")
assert(edad_num < 150, "La edad no es válida")

unless edad_num >= 18
    say("Debes ser mayor de edad")
    exit(1)
end

say("¡Bienvenido!")
```

### Procesamiento con Feedback

```mux
let archivos = ["doc1.txt", "doc2.txt", "doc3.txt"]

each archivo in archivos
    show("Procesando: " + archivo)
    wait(1)
    say("✓ Completado: " + archivo)
end

say("¡Todos los archivos procesados!")
```

### Menú Interactivo

```mux
loop
    print("")
    print("=== Menú ===")
    print("1. Opción 1")
    print("2. Opción 2")
    print("3. Salir")
    
    let opcion = ask("Selecciona una opción")
    let opt = int(opcion)
    
    if opt == 1
        say("Ejecutando opción 1...")
    elif opt == 2
        say("Ejecutando opción 2...")
    elif opt == 3
        say("¡Hasta luego!")
        exit(0)
    else
        say("Opción no válida")
    end
end
```

### Validación con Assert

```mux
func dividir(a, b)
    assert(b != 0, "No se puede dividir por cero")
    return a / b
end

let resultado = dividir(10, 2)
show(resultado)  # 👁️ 5

let resultado2 = dividir(10, 0)
# ❌ Assert: No se puede dividir por cero
```

---

## 📊 Comparación con Otros Lenguajes

| Mux | Python | JavaScript | Ruby |
|-----|--------|------------|------|
| `show()` | `print()` | `console.log()` | `puts` |
| `say()` | `print()` | `console.log()` | `puts` |
| `ask()` | `input()` | `prompt()` | `gets` |
| `unless` | `if not` | - | `unless` |
| `until` | `while not` | - | `until` |
| `each` | `for` | `forEach` | `each` |
| `loop` | `while True` | `while(true)` | `loop` |
| `pass` | `pass` | - | - |
| `assert` | `assert` | - | - |

---

## 🎨 Filosofía de Diseño

Los comandos únicos de Mux están diseñados para:

1. **Expresividad**: Código más natural y legible
2. **Feedback Visual**: Emojis para mejor UX
3. **Simplicidad**: Menos código, más claro
4. **Consistencia**: Sintaxis uniforme

---

**Creado por MushhX** 🌍⚙️
