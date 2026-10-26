# Benchmarks

Los microbenchmarks permiten comparar cambios del intérprete:

```console
mux --time benchmarks/sum_100k.mux
mux --time benchmarks/interpreter_suite.mux
```

El primer archivo mide una suma; el segundo recorre bucles, llamadas y crecimiento de listas. La salida informa duración, pasos y pasos por segundo. Ejecuta cada comando varias veces en la misma máquina y compara medianas; registra versión de Mux, sistema operativo y runtime anfitrión. Son cargas pequeñas, no sustituyen el perfilado de una aplicación real ni miden el pico de memoria.
