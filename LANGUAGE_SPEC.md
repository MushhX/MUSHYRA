# Especificación del lenguaje Mux

Esta referencia describe la sintaxis que implementa el parser. Las columnas de los diagnósticos cuentan puntos de código Unicode; las tabulaciones ocupan una columna de origen y se expanden al presentar el cursor en la terminal. Los finales CRLF y CR se normalizan a LF antes de tokenizar.

## Léxico

- Los identificadores empiezan por una letra Unicode o `_`, y continúan con letras, cifras o `_`. El token de identificador se normaliza a Unicode NFC.
- Los números admiten enteros, decimales y exponente decimal; se pueden usar `_` entre cifras: `1_000`, `3.14`, `2e6`.
- Las cadenas usan comillas dobles y escapes `\"`, `\\`, `\b`, `\n`, `\r`, `\t`, `\f` y `\uXXXX`. No admiten saltos de línea dentro de una cadena.
- `#` inicia un comentario hasta el fin de línea.
- Los saltos de línea separan declaraciones. Dentro de `()`, `[]` y `{}` se pueden partir expresiones en varias líneas.

## Gramática EBNF

```ebnf
program       = { newline | statement newline } ;
statement     = import | declaration | assignment | call | print | conditional
              | loop | function | flow | assertion | display | pass ;
import        = "import" module [ "as" identifier ]
              | "from" module "import" identifier [ "as" identifier ]
                { "," identifier [ "as" identifier ] } ;
module        = identifier { "." identifier } ;
declaration   = "let" identifier "=" expression ;
assignment    = target "=" expression ;
target        = identifier | postfix "[" expression "]" | postfix "." identifier ;
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
function      = "func" identifier "(" [ identifier { "," identifier } [ "," ] ] ")"
                block "end" ;
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
postfix       = primary { "[" expression "]" | "." identifier [ arguments ] } ;
primary       = number | string | boolean | "null" | identifier [ arguments ]
              | "(" expression ")" | list | dictionary | builtin ;
arguments     = "(" [ expression { "," expression } [ "," ] ] ")" ;
list          = "[" [ expression { "," expression } [ "," ] ] "]" ;
dictionary    = "{" [ expression ":" expression { "," expression ":" expression } [ "," ] ] "}" ;
builtin       = ("input" | "ask" | "len" | "type" | "str" | "int" | "float" | "range") arguments ;
boolean       = "true" | "false" ;
```

The parser evaluates comparison chains from left to right; they are not Python-style chained comparisons. Logical operators return booleans and short-circuit. Numeric equality permits integer/float comparison; other equality requires matching Mux types. Truthiness follows Python conventions for empty values, zero, `false` and `null`.

Functions currently take positional arguments only. Calls to variables use `name(...)`; module functions use `module.function(...)`. Statement separators are newlines, and every block closes with `end`.
