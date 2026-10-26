"""Build a standalone MUSHYRA executable for the current operating system."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "mux_main.py"


def build_executable():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller no está instalado. Ejecuta: pip install -e .[build]", file=sys.stderr)
        return 1
    if not ENTRYPOINT.is_file():
        print(f"No existe el punto de entrada {ENTRYPOINT}", file=sys.stderr)
        return 1

    output_dir = ROOT / "dist"
    work_dir = ROOT / "build" / "pyinstaller-work"
    spec_dir = ROOT / "build" / "pyinstaller-spec"
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "PyInstaller", "--onefile", "--noconfirm", "--clean",
        "--name", "myr", "--distpath", str(output_dir), "--workpath", str(work_dir),
        "--specpath", str(spec_dir), str(ENTRYPOINT),
    ]
    print("Compilando MUSHYRA para la plataforma actual...")
    try:
        result = subprocess.run(command, cwd=str(ROOT), check=False)
    except OSError as exc:
        print(f"No se pudo iniciar PyInstaller: {exc}", file=sys.stderr)
        return 1
    if result.returncode:
        return result.returncode

    suffix = ".exe" if os.name == "nt" else ""
    artifact = output_dir / f"myr{suffix}"
    if not artifact.is_file():
        print(f"PyInstaller terminó sin crear {artifact}", file=sys.stderr)
        return 1
    legacy_artifact = output_dir / f"mux{suffix}"
    shutil.copy2(artifact, legacy_artifact)
    print(f"Ejecutable creado: {artifact}")
    print(f"Alias de compatibilidad creado: {legacy_artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_executable())
