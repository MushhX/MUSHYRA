# Benchmarks

Los microbenchmarks permiten comparar cambios del intérprete:

```console
myr --time benchmarks/sum_100k.myr
myr --time benchmarks/interpreter_suite.myr
```

El primer archivo mide una suma; el segundo recorre bucles, llamadas y crecimiento de listas. La salida informa duración, pasos y pasos por segundo. Ejecuta cada comando varias veces en la misma máquina y compara medianas; registra versión de MUSHYRA, sistema operativo y runtime anfitrión. Son cargas pequeñas, no sustituyen el perfilado de una aplicación real ni miden el pico de memoria.
