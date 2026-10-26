# Benchmarks

`sum_100k.mux` is a small, stable workload for comparing interpreter changes:

```console
mux --time benchmarks/sum_100k.mux
```

It prints the expected sum and reports elapsed interpreter time to stderr. Run it several times on the same machine, compare medians, and record the Mux version, OS, and Python runtime used to host Mux. This is a smoke workload, not a substitute for profiling a representative application; it does not measure peak memory.
