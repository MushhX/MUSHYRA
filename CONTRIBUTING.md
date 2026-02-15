# Contribuir a Mux 🤝

¡Gracias por tu interés en contribuir a Mux! Este proyecto busca ser una comunidad abierta y acogedora.

## Filosofía del Proyecto

Antes de contribuir, ten en cuenta los principios de Mux:
- **Claridad sobre complejidad**: Preferimos código legible a código "inteligente"
- **Mensajes de error útiles**: Los errores deben ayudar, no confundir
- **Documentación accesible**: Escribe para principiantes
- **Minimalismo**: Solo añade lo necesario

## Cómo Contribuir

### Reportar Bugs
1. Verifica que el bug no esté ya reportado
2. Incluye un ejemplo mínimo reproducible
3. Describe el comportamiento esperado vs el actual
4. Incluye tu versión de Python y sistema operativo

### Proponer Nuevas Características
1. Abre un issue primero para discutir la idea
2. Explica el caso de uso y por qué es importante
3. Considera si encaja con la filosofía minimalista de Mux

### Enviar Pull Requests
1. Fork el repositorio
2. Crea una rama para tu feature: `git checkout -b feature/mi-feature`
3. Escribe código claro y bien comentado
4. Añade ejemplos si introduces nueva sintaxis
5. Actualiza la documentación si es necesario
6. Asegúrate de que todos los ejemplos funcionen
7. Commit con mensajes descriptivos
8. Push y abre un Pull Request

## Estructura del Código

```
mux.py          # Intérprete principal (Lexer, Parser, Interpreter)
examples/       # Ejemplos de código Mux
README.md       # Documentación principal
ROADMAP.md      # Plan de desarrollo
```

## Estilo de Código

- Sigue PEP 8 para código Python
- Usa nombres descriptivos en español para ejemplos
- Comenta código complejo
- Mantén funciones pequeñas y enfocadas

## Testing

Antes de enviar un PR, verifica que todos los ejemplos funcionen:

```bash
python mux.py examples/hola_mundo.mux
python mux.py examples/variables.mux
python mux.py examples/condicionales.mux
python mux.py examples/bucles.mux
python mux.py examples/funciones.mux
python mux.py examples/calculadora.mux
python mux.py examples/fibonacci.mux
```

## Código de Conducta

- Sé respetuoso y constructivo
- Acepta críticas con mente abierta
- Enfócate en lo mejor para el proyecto
- Ayuda a otros a aprender

## Preguntas

Si tienes dudas, abre un issue con la etiqueta "question".

¡Gracias por hacer de Mux un mejor lenguaje! 🌍⚙️
