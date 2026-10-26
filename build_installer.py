"""Build the Windows installer with Inno Setup."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from mux_lang._version import __version__


ROOT = Path(__file__).resolve().parent


def find_inno_setup():
    executable = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if executable:
        return Path(executable)
    for candidate in (
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
    ):
        if candidate.is_file():
            return candidate
    return None


def build_installer():
    if sys.platform != "win32":
        print("El instalador Inno Setup solo se puede crear en Windows", file=sys.stderr)
        return 1
    if sys.maxsize <= 2 ** 32:
        print("Compila el instalador con Python de 64 bits", file=sys.stderr)
        return 1
    executable = ROOT / "dist" / "myr.exe"
    if not executable.is_file():
        print("No existe dist/myr.exe; ejecuta primero python build_exe.py", file=sys.stderr)
        return 1
    compiler = find_inno_setup()
    if compiler is None:
        print("No se encontró Inno Setup 6 (ISCC.exe)", file=sys.stderr)
        return 1

    icon = ROOT / "mux_icon.ico"
    if not icon.is_file():
        try:
            result = subprocess.run([sys.executable, str(ROOT / "create_icon.py")], cwd=str(ROOT), check=False)
        except OSError as exc:
            print(f"No se pudo crear el icono: {exc}", file=sys.stderr)
            return 1
        if result.returncode or not icon.is_file():
            print('No se creó mux_icon.ico. Instala las dependencias con python -m pip install ".[build]"', file=sys.stderr)
            return 1

    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    template_path = ROOT / "installer.iss"
    generated = build_dir / "installer.generated.iss"
    template = template_path.read_text(encoding="utf-8")
    template = template.replace("@MUX_VERSION@", __version__)
    template = template.replace("@MUX_ROOT@", str(ROOT.resolve()).replace("/", "\\"))
    template = template.replace("@MUX_OUTPUT_DIR@", str((ROOT / "installer_output").resolve()).replace("/", "\\"))
    with generated.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(template)
    output_dir = ROOT / "installer_output"
    output_dir.mkdir(exist_ok=True)
    try:
        result = subprocess.run(
            [str(compiler), "/Qp", str(generated)],
            cwd=str(ROOT), check=False,
        )
    except OSError as exc:
        print(f"No se pudo iniciar Inno Setup: {exc}", file=sys.stderr)
        return 1
    if result.returncode:
        return result.returncode
    artifact = output_dir / f"mushyra-setup-{__version__}.exe"
    if not artifact.is_file():
        print(f"Inno Setup terminó sin crear {artifact}", file=sys.stderr)
        return 1
    print(f"Instalador creado: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_installer())
