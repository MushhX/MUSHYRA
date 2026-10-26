# Especificación del lenguaje MUSHYRA

Esta referencia describe la sintaxis que implementa el parser. Las columnas de los diagnósticos cuentan puntos de código Unicode; las tabulaciones ocupan una columna de origen y se expanden al presentar el cursor en la terminal. Los finales CRLF y CR se normalizan a LF antes de tokenizar.

## Léxico

- Los identificadores empiezan por una letra Unicode o `_`, y continúan con letras, cifras o `_`. El token de identificador se normaliza a Unicode NFC.
- Los números admiten enteros, decimales y exponente decimal; se pueden usar `_` entre cifras: `1_000`, `3.14`, `2e6`.
- Las cadenas usan comillas dobles y escapes `\"`, `\\`, `\b`, `\n`, `\r`, `\t`, `\f` y `\uXXXX`. No admiten saltos de línea dentro de una cadena.
- `#` inicia un comentario hasta el fin de línea.
- Los saltos de línea separan declaraciones. Dentro de `()`, `[]` y `{}` se pueden partir expresiones en varias líneas.
- Los identificadores se normalizan a NFC; el contenido de strings no se normaliza. `len`, índices y slices de strings cuentan puntos de código Unicode, no grafemas visibles, por lo que un emoji combinado puede ocupar varios índices.

## Gramática EBNF

```ebnf
program       = { newline | statement newline } ;
statement     = import | declaration | assignment | call | print | conditional
              | loop | function | flow | assertion | display | pass ;
import        = "import" module [ "as" identifier ]
              | "from" module "import" identifier [ "as" identifier ]
                { "," identifier [ "as" identifier ] } ;
module        = identifier { "." identifier } ;
declaration   = "let" ( identifier | pattern ) "=" expression ;
assignment    = target "=" expression ;
target        = identifier | pattern | postfix "[" expression "]"
              | postfix "[" [ expression ] ":" [ expression ] [ ":" [ expression ] ] "]"
              | postfix "." identifier ;
pattern       = identifier | "[" pattern { "," pattern } [ "," ] "]"
              | "(" pattern ")" | "(" pattern "," [ pattern { "," pattern } [ "," ] ] ")"
              | "{" pattern_entry { "," pattern_entry } [ "," ] "}" ;
pattern_entry = identifier [ ":" pattern ] | string ":" pattern ;
print         = "print" "(" expression ")" ;
conditional   = "if" expression block { "elif" expression block }
                [ "else" block ] "end"
              | "unless" expression block "end" ;
loop          = "repeat" expression block
              | "while" expression block
              | "for" identifier "in" expression block
              | "each" identifier "in" expression block
              | "loop" block
              | "until" expression block
              | number "times" [ "do" ] block ;
function      = "func" identifier "(" [ parameter { "," parameter } [ "," ] ] ")"
                block "end" ;
parameter     = [ "*" ] identifier [ "=" expression ] ;
flow          = "return" [ expression ] | "break" | "continue"
              | "exit" [ "(" [ expression ] ")" | expression ]
              | "global" identifier { "," identifier }
              | "nonlocal" identifier { "," identifier } ;
assertion     = "assert" "(" expression [ "," expression ] ")" ;
display       = ("show" | "say" | "wait") "(" expression ")"
              | "ask" "(" expression ")" ;
pass          = "pass" ;
block         = newline { statement newline } ;
expression   = logical_or ;
logical_or    = logical_and { "||" logical_and } ;
logical_and   = comparison { "&&" comparison } ;
comparison    = additive { ("==" | "!=" | "<" | ">" | "<=" | ">=") additive } ;
additive      = multiplicative { ("+" | "-") multiplicative } ;
multiplicative= unary { ("*" | "/" | "%") unary } ;
unary         = ("!" | "-") unary | postfix ;
postfix       = primary { "[" expression "]"
              | "[" [ expression ] ":" [ expression ] [ ":" [ expression ] ] "]"
              | "." identifier [ arguments ] } ;
primary       = number | string | boolean | "null" | identifier [ arguments ]
              | "(" expression ")" | tuple | list | dictionary | builtin ;
tuple         = "(" ")" | "(" expression "," [ expression { "," expression } [ "," ] ] ")" ;
arguments     = "(" [ argument { "," argument } [ "," ] ] ")" ;
argument      = identifier "=" expression | expression ;
list          = "[" [ expression { "," expression } [ "," ] | expression "for" identifier "in" expression [ "if" expression ] ] "]" ;
dictionary    = "{" [ expression ":" expression { "," expression ":" expression } [ "," ]
              | expression ":" expression "for" identifier "in" expression [ "if" expression ] ] "}" ;
builtin       = ("input" | "ask" | "len" | "type" | "str" | "int" | "float" | "range") arguments ;
boolean       = "true" | "false" ;
```

The parser evaluates comparison chains from left to right; they are not Python-style chained comparisons. Logical operators return booleans and short-circuit. Numeric equality permits integer/float comparison; booleans are not numbers. Lists, tuples, and dictionaries compare recursively, and other equality requires matching MUSHYRA types. Truthiness is false for `null`, `false`, zero, and empty strings, lists, tuples, dictionaries, or ranges; other values are true.

`+` accepts two numbers or two sequences of the same type (strings, lists, or tuples). `-`, `/`, and `%` accept numbers. `*` accepts two numbers or a string/list/tuple and an integer. Ordering comparisons accept two numbers or two strings. Unsupported combinations raise a MUSHYRA diagnostic instead of inheriting Python's implicit coercions. Dictionary keys retain Python's hashable-key behavior for compatibility.

Functions use lexical bindings. A name assigned anywhere in a function is local throughout that function unless declared `global` or `nonlocal`; reading a local before its first assignment is an error. `nonlocal` must refer to a binding in an enclosing function. The resolver reports these errors before the program starts running.

Functions accept positional and named arguments, trailing default parameters, and one final variadic parameter. For example, `func greet(name, prefix="Hola", *extras)` can be called as `greet("Ana")`, `greet(name="Ana")`, or `greet("Ana", "Buenas", 1, 2)`, where `extras` is a list. Required parameters must precede parameters with defaults and the variadic parameter; positional arguments must precede named arguments; duplicate, unknown, or missing arguments are errors. Defaults are evaluated once when the function definition executes. Native functions continue to accept positional arguments only. Calls to variables use `name(...)`; module functions use `module.function(...)`. Statement separators are newlines, and every block closes with `end`.

Parentheses group expressions; a comma creates an immutable tuple, including the one-element form `(value,)` and empty form `()`. List and dictionary comprehensions evaluate their iterable once, bind the iteration variable in a temporary local scope, and optionally filter each item with `if`; for example, `[value * 2 for value in numbers if value > 0]` and `{value: value * 2 for value in numbers}`. Comprehensions accept at most one iteration clause and are limited to one million input elements.

Sequence destructuring binds values after the complete pattern has been checked: `let [first, [second, third]] = values` or `let (first, second) = pair`. Dictionary patterns select named keys and can rename them: `let {name: person, age} = record` binds `record["name"]` to `person` and `record["age"]` to `age`; extra keys are allowed, but every requested key must exist. Assignment uses the same nested patterns without `let`. A sequence pattern must match its length exactly; lists, tuples, strings, and ranges can be unpacked. Slices use Python-style exclusive endpoints on lists, tuples, strings, and ranges, such as `items[1:4]`, `text[::-1]`, or `values[:limit:2]`. A slice can be assigned on the left side of an assignment only when the target is a list; the replacement must be a sequence, and extended slices must have the same length as the selected elements.
