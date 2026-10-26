"""Local and checksum-verified package management for Mux source modules."""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time
import urllib.request
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit


MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_PACKAGE_FILES = 10_000


def _mux_home() -> Path:
    configured = os.environ.get("MUX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return (base / "Mux").resolve()
    base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return (base / "mux").resolve()


MUX_HOME = _mux_home()
PACKAGES_DIR = MUX_HOME / "packages"
REGISTRY_FILE = MUX_HOME / "registry.json"
LOCK_FILE = MUX_HOME / "registry.lock"
PACKAGE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
REGISTRY_VERSION = 1
WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def init_package_system() -> None:
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    MUX_HOME.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        _write_registry({"schema_version": REGISTRY_VERSION, "packages": {}})


@contextmanager
def _registry_lock(timeout: float = 10.0):
    """Cross-platform exclusive lock with recovery for abandoned lock files."""
    MUX_HOME.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    descriptor = None
    while descriptor is None:
        try:
            descriptor = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(descriptor, str(os.getpid()).encode("ascii"))
        except FileExistsError:
            try:
                if time.time() - LOCK_FILE.stat().st_mtime > 120:
                    LOCK_FILE.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError(f"No se pudo adquirir el bloqueo de {REGISTRY_FILE}")
            time.sleep(0.05)
    try:
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            LOCK_FILE.unlink()
        except FileNotFoundError:
            pass


def _empty_registry():
    return {"schema_version": REGISTRY_VERSION, "packages": {}}


def _read_registry():
    if not REGISTRY_FILE.exists():
        return _empty_registry()
    try:
        with REGISTRY_FILE.open("r", encoding="utf-8") as stream:
            registry = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        backup = REGISTRY_FILE.with_suffix(".json.corrupt")
        try:
            shutil.copy2(REGISTRY_FILE, backup)
        except OSError:
            backup = None
        suffix = f" Se guardó una copia en {backup}." if backup else ""
        raise RuntimeError(f"El registro de paquetes está dañado: {exc}.{suffix}") from exc
    if isinstance(registry, dict) and "packages" not in registry:
        # Migrate the original name -> metadata dictionary in-place.
        registry = {"schema_version": REGISTRY_VERSION, "packages": registry}
    if not isinstance(registry, dict) or not isinstance(registry.get("packages"), dict):
        raise RuntimeError("El formato del registro de paquetes no es válido")
    for name, metadata in registry["packages"].items():
        try:
            _validate_name(name)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("El registro contiene un nombre de paquete no válido") from exc
        if not isinstance(metadata, dict):
            raise RuntimeError(f"Los metadatos del paquete {name!r} no son válidos")
    registry["schema_version"] = REGISTRY_VERSION
    return registry


def _write_registry(registry):
    MUX_HOME.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="registry-", suffix=".tmp", dir=str(MUX_HOME))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(registry, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, REGISTRY_FILE)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _validate_name(name: str) -> str:
    if not PACKAGE_NAME_RE.fullmatch(name or ""):
        raise ValueError("El nombre debe empezar por letra o _ y contener solo letras, números y _ (máx. 64)")
    if name.casefold() in WINDOWS_RESERVED_NAMES:
        raise ValueError("El nombre coincide con un nombre de dispositivo reservado")
    return name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_extract(archive: zipfile.ZipFile, destination: Path):
    total_size = 0
    seen_paths = set()
    if len(archive.infolist()) > MAX_PACKAGE_FILES:
        raise ValueError(f"El ZIP supera el límite de {MAX_PACKAGE_FILES} archivos")
    for member in archive.infolist():
        total_size += member.file_size
        if member.file_size > 20 * 1024 * 1024 or total_size > 100 * 1024 * 1024:
            raise ValueError("El ZIP supera el límite de 20 MB por archivo o 100 MB total")
        raw = member.filename
        if "\\" in raw:
            raise ValueError(f"Ruta no válida en ZIP: {raw!r}")
        relative = PurePosixPath(raw)
        if relative.is_absolute() or not relative.parts or any(part in ("..", "") for part in relative.parts):
            raise ValueError(f"Ruta no segura en ZIP: {raw!r}")
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError(f"No se permiten enlaces simbólicos en ZIP: {raw!r}")
        if any(":" in part for part in relative.parts):
            raise ValueError(f"Ruta absoluta no permitida en ZIP: {raw!r}")
        for part in relative.parts:
            if part.split(".", 1)[0].casefold() in WINDOWS_RESERVED_NAMES:
                raise ValueError(f"Nombre reservado no permitido en ZIP: {raw!r}")
        normalized_name = relative.as_posix().casefold().rstrip("/")
        if normalized_name in seen_paths:
            raise ValueError(f"Ruta duplicada en ZIP: {raw!r}")
        seen_paths.add(normalized_name)
        target = destination.joinpath(*relative.parts)
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if target.suffix.lower() not in (".mux", ".json", ".md", ".txt"):
            raise ValueError(f"Tipo de archivo no permitido en paquete Mux: {raw!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)


def _stage_source(source: str, staging: Path, expected_sha256=None):
    if expected_sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("--sha256 debe contener 64 caracteres hexadecimales")
    source_scheme = urlsplit(source).scheme.lower()
    if source_scheme == "https":
        if not expected_sha256:
            raise ValueError("Las URL HTTPS requieren --sha256 para comprobar el paquete")
        filename = staging / "download.zip"
        request = urllib.request.Request(source, headers={"User-Agent": "Mux-Package-Manager/1"})
        with urllib.request.urlopen(request, timeout=30) as response, filename.open("wb") as target:
            if urlsplit(response.geturl()).scheme.lower() != "https":
                raise ValueError("La descarga fue redirigida fuera de HTTPS")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
                raise ValueError("El ZIP remoto supera el límite de 50 MiB")
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError("El ZIP remoto supera el límite de 50 MiB")
                target.write(chunk)
        actual = _sha256(filename)
        if actual.lower() != expected_sha256.lower():
            raise ValueError(f"SHA-256 no coincide: esperado {expected_sha256}, recibido {actual}")
        with zipfile.ZipFile(filename) as archive:
            _safe_extract(archive, staging / "package")
        parsed = urlsplit(source)
        hostname = parsed.hostname or ""
        if ":" in hostname:
            hostname = f"[{hostname}]"
        if parsed.port:
            hostname += f":{parsed.port}"
        safe_source = urlunsplit((parsed.scheme, hostname, parsed.path, "", ""))
        return actual, safe_source
    if source_scheme == "http":
        raise ValueError("Las descargas de paquetes solo admiten HTTPS")

    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"No existe el origen {source!r}; usa una ruta local o una URL HTTPS con --sha256")
    if path.is_file() and path.suffix.lower() == ".mux":
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("El archivo .mux supera el límite de 20 MiB")
        package_dir = staging / "package"
        package_dir.mkdir()
        shutil.copy2(path, package_dir / path.name)
        actual = _sha256(path)
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise ValueError("SHA-256 no coincide con el archivo .mux")
        return actual, str(path)
    if path.is_file() and zipfile.is_zipfile(path):
        if path.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("El ZIP local supera el límite de 50 MiB")
        actual = _sha256(path)
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise ValueError("SHA-256 no coincide con el ZIP")
        package_dir = staging / "package"
        package_dir.mkdir()
        with zipfile.ZipFile(path) as archive:
            _safe_extract(archive, package_dir)
        return actual, str(path)
    if path.is_dir():
        package_dir = staging / "package"
        package_dir.mkdir()
        copied_files = 0
        copied_bytes = 0
        seen_paths = set()
        for item in path.rglob("*"):
            if item.is_symlink():
                raise ValueError(f"No se permiten enlaces simbólicos: {item}")
            if item.is_file() and item.suffix.lower() in (".mux", ".json", ".md", ".txt"):
                copied_files += 1
                file_size = item.stat().st_size
                copied_bytes += file_size
                if file_size > 20 * 1024 * 1024:
                    raise ValueError(f"El archivo {item.name!r} supera el límite de 20 MiB")
                if copied_files > MAX_PACKAGE_FILES or copied_bytes > 100 * 1024 * 1024:
                    raise ValueError("El paquete local supera el límite de archivos o 100 MiB")
                relative = PurePosixPath(item.relative_to(path).as_posix())
                if "\\" in relative.as_posix() or any(":" in part for part in relative.parts):
                    raise ValueError(f"Ruta no portable en paquete local: {relative}")
                if any(part.split(".", 1)[0].casefold() in WINDOWS_RESERVED_NAMES for part in relative.parts):
                    raise ValueError(f"Nombre reservado en paquete local: {relative}")
                normalized_name = relative.as_posix().casefold()
                if normalized_name in seen_paths:
                    raise ValueError(f"Ruta duplicada en paquete local: {relative}")
                seen_paths.add(normalized_name)
                target = package_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
        digest = hashlib.sha256()
        for item in sorted(p for p in package_dir.rglob("*") if p.is_file()):
            digest.update(item.relative_to(package_dir).as_posix().encode("utf-8"))
            digest.update(item.read_bytes())
        actual = digest.hexdigest()
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise ValueError("SHA-256 del contenido de la carpeta no coincide")
        return actual, str(path)
    raise ValueError("El origen debe ser una carpeta, un .mux, un ZIP o una URL HTTPS")


def _prepare_entrypoint(package_dir: Path, package_name: str):
    manifest_path = package_dir / "mux-package.json"
    manifest = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"mux-package.json no válido: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ValueError("mux-package.json debe contener un objeto JSON")
    name = _validate_name(str(manifest.get("name", package_name)))
    main = manifest.get("main")
    if main:
        main_path = (package_dir / str(main)).resolve()
        if package_dir.resolve() not in main_path.parents or main_path.suffix.lower() != ".mux" or not main_path.is_file():
            raise ValueError("El campo main debe apuntar a un archivo .mux dentro del paquete")
    else:
        expected = package_dir / f"{name}.mux"
        mux_files = sorted(package_dir.rglob("*.mux"))
        if expected.is_file():
            main_path = expected
        elif len(mux_files) == 1:
            main_path = mux_files[0]
        else:
            raise ValueError("Define 'main' en mux-package.json o incluye un único .mux de entrada")
    target = package_dir / f"{name}.mux"
    if main_path != target:
        shutil.copy2(main_path, target)
    return name, manifest


def list_packages(as_json: bool = False):
    init_package_system()
    registry = _read_registry()
    packages = registry["packages"]
    if as_json:
        print(json.dumps(packages, ensure_ascii=False, indent=2, sort_keys=True))
        return packages
    if not packages:
        print("No hay paquetes instalados")
        return packages
    print("Paquetes Mux instalados:\n")
    for name, info in sorted(packages.items()):
        print(f"  {name} ({info.get('version', 'sin versión')})")
        print(f"    {info.get('description', 'Sin descripción')}")
        print(f"    {info.get('installed_at', 'fecha desconocida')}\n")
    return packages


def install_package(source: str, name: str = None, sha256: str = None):
    init_package_system()
    if urlsplit(source).scheme.lower() == "https" and not name:
        raise ValueError("Las URL HTTPS requieren --name para definir el nombre del módulo")
    source_path = Path(source).expanduser()
    inferred_name = source_path.stem if source_path.is_file() else source_path.name
    package_name = _validate_name(name or inferred_name)
    with tempfile.TemporaryDirectory(prefix="mux-package-") as temp_name:
        staging_root = Path(temp_name)
        digest, source_label = _stage_source(source, staging_root, sha256)
        package_dir = staging_root / "package"
        if not package_dir.is_dir():
            raise ValueError("El paquete no contiene archivos")
        manifest_name, manifest = _prepare_entrypoint(package_dir, package_name)
        if name and manifest_name != name:
            raise ValueError(f"El nombre del manifiesto ({manifest_name}) no coincide con --name ({name})")
        package_name = _validate_name(manifest_name)
        files = sorted(item.relative_to(package_dir).as_posix() for item in package_dir.rglob("*") if item.is_file())
        if not any(item.endswith(".mux") for item in files):
            raise ValueError("El paquete debe incluir al menos un archivo .mux")

        target = PACKAGES_DIR / package_name
        install_stage = staging_root / "ready"
        shutil.copytree(package_dir, install_stage)
        metadata = {
            "version": str(manifest.get("version", "0.0.0")),
            "description": str(manifest.get("description", f"Módulo Mux {package_name}")),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": source_label,
            "sha256": digest,
            "files": files,
            "install_path": str(target),
        }
        backup = staging_root / "previous"
        with _registry_lock():
            registry = _read_registry()
            had_previous = target.exists()
            if had_previous:
                os.replace(target, backup)
            try:
                os.replace(install_stage, target)
                registry["packages"][package_name] = metadata
                _write_registry(registry)
            except Exception:
                if target.exists():
                    shutil.rmtree(target)
                if had_previous and backup.exists():
                    os.replace(backup, target)
                raise
    print(f"Paquete {package_name} instalado en {target}")
    return metadata


def uninstall_package(package_name: str):
    init_package_system()
    package_name = _validate_name(package_name)
    target = (PACKAGES_DIR / package_name).resolve()
    if target.parent != PACKAGES_DIR.resolve():
        raise ValueError("Ruta de instalación no válida")
    with _registry_lock():
        registry = _read_registry()
        if package_name not in registry["packages"]:
            print(f"Paquete {package_name} no está instalado")
            return False
        entry = registry["packages"].pop(package_name)
        recorded_path = Path(entry.get("install_path", target)).resolve()
        if recorded_path != target:
            raise RuntimeError("El registro contiene una ruta de paquete no válida; no se eliminó ningún archivo")
        quarantine = PACKAGES_DIR / f".{package_name}.remove-{os.getpid()}"
        if quarantine.exists():
            shutil.rmtree(quarantine)
        if target.exists():
            os.replace(target, quarantine)
        try:
            _write_registry(registry)
        except Exception:
            if quarantine.exists():
                os.replace(quarantine, target)
            raise
        if quarantine.exists():
            shutil.rmtree(quarantine)
    print(f"Paquete {package_name} desinstalado")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mux-pkg", description="Instala módulos Mux locales o desde una URL HTTPS verificada")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="Lista paquetes instalados")
    list_parser.add_argument("--json", action="store_true", help="Imprime el registro como JSON")
    install_parser = subparsers.add_parser("install", help="Instala una carpeta, un archivo .mux o un ZIP")
    install_parser.add_argument("source", help="Ruta local o URL HTTPS a un ZIP")
    install_parser.add_argument("--name", help="Nombre de importación del paquete")
    install_parser.add_argument("--sha256", help="Hash SHA-256 obligatorio para una URL HTTPS")
    remove_parser = subparsers.add_parser("remove", aliases=["uninstall"], help="Desinstala un paquete")
    remove_parser.add_argument("name")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            list_packages(args.json)
        elif args.command == "install":
            install_package(args.source, args.name, args.sha256)
        elif args.command in ("remove", "uninstall"):
            if not uninstall_package(args.name):
                return 1
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"mux-pkg: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
