# Obtener MUSHYRA

El repositorio no versiona binarios precompilados ni hashes verificados de una release. Para obtener una copia ejecutable, compílala localmente.

## Código fuente

```console
git clone https://github.com/MushhX/Mux.git
cd Mux
python -m pip install .
```

## Ejecutable local

```console
python -m pip install ".[build]"
python build_exe.py
```

El binario se genera en `dist/` para la plataforma actual. En Windows, consulta [INSTALLER_GUIDE.md](INSTALLER_GUIDE.md) para crear un instalador; `python create_portable_installer.py` crea un ZIP portable.

Verifica los artefactos que construyas con los hashes generados por el propio proceso de distribución. No reutilices nombres, tamaños o hashes publicados en documentos antiguos.
