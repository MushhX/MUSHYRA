"""Create a reproducible portable ZIP for the current platform."""

import argparse
import hashlib
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from mushyra._version import __version__


ROOT = Path(__file__).resolve().parent
DOCS = (
    "README.md", "LICENSE", "QUICKSTART.md", "FEATURES.md", "STDLIB_REFERENCE.md",
    "UNIQUE_COMMANDS.md", "EXECUTABLE_GUIDE.md", "INSTALL.md",
)


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_text(path, content):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def _write_metadata(staging):
    platform_tag = f"{platform.system().lower()}-{platform.machine().lower()}"
    binary = "myr.exe" if os.name == "nt" else "myr"
    install_text = f"""MUSHYRA {__version__} — paquete portable

1. Extrae esta carpeta.
2. Ejecuta {binary} examples/hola_mundo.myr.
3. Consulta README.md y QUICKSTART.md.

Las integraciones opcionales estarán incluidas solo si sus dependencias se
instalaron en el entorno de compilación. SHA256SUMS.txt contiene los hashes
de los archivos incluidos.
"""
    _write_text(staging / "INSTALL.txt", install_text)
    _write_text(
        staging / "VERSION.txt",
        f"MUSHYRA {__version__}\nPlatform: {platform_tag}\nArchitecture: {platform.machine()}\n",
    )
    manifest = []
    for path in sorted(staging.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            manifest.append(f"{_sha256(path)}  {path.relative_to(staging).as_posix()}")
    _write_text(staging / "SHA256SUMS.txt", "\n".join(manifest) + "\n")
    return platform_tag


def create_portable_installer(output_dir=None):
    suffix = ".exe" if os.name == "nt" else ""
    executable = ROOT / "dist" / f"myr{suffix}"
    if not executable.is_file():
        print(f"No se encontró {executable}; ejecuta primero python build_exe.py", file=sys.stderr)
        return 1
    output = Path(output_dir).expanduser().resolve() if output_dir else ROOT
    output.mkdir(parents=True, exist_ok=True)
    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="myr-portable-", dir=str(build_dir)) as temp_name:
            staging = Path(temp_name) / "myr"
            staging.mkdir()
            shutil.copy2(executable, staging / executable.name)
            shutil.copytree(ROOT / "examples", staging / "examples")
            for name in DOCS:
                source = ROOT / name
                if source.is_file():
                    shutil.copy2(source, staging / source.name)
            platform_tag = _write_metadata(staging)
            archive_path = output / f"mushyra-portable-v{__version__}-{platform_tag}.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for path in sorted(staging.rglob("*")):
                    if not path.is_file():
                        continue
                    name = path.relative_to(staging.parent).as_posix()
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    except (OSError, shutil.Error, zipfile.BadZipFile) as exc:
        print(f"No se pudo crear el paquete portable: {exc}", file=sys.stderr)
        return 1
    print(f"Paquete portable creado: {archive_path} ({archive_path.stat().st_size} bytes)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Crea un ZIP portable de MUSHYRA")
    parser.add_argument("--output-dir", help="Carpeta de salida; por defecto el repositorio")
    args = parser.parse_args(argv)
    return create_portable_installer(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
