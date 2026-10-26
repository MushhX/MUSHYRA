"""Local and checksum-verified package management for Mux source modules."""

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import stat
import sys
import tempfile
import time
import unicodedata
import urllib.request
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_PACKAGE_FILES = 10_000
MAX_PACKAGE_BYTES = 100 * 1024 * 1024
MAX_REGISTRY_INDEX_BYTES = 5 * 1024 * 1024
PACKAGE_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$")


def _mux_home() -> Path:
    configured = os.environ.get("MYR_HOME") or os.environ.get("MUX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        current = base / "MUSHYRA"
        legacy = base / "Mux"
        return (current if current.exists() or not legacy.exists() else legacy).resolve()
    base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    current = base / "myr"
    legacy = base / "mux"
    return (current if current.exists() or not legacy.exists() else legacy).resolve()


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
    if os.name != "nt":
        try:
            os.chmod(MUX_HOME, 0o700)
            os.chmod(PACKAGES_DIR, 0o700)
        except OSError:
            pass
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
                age = time.time() - LOCK_FILE.stat().st_mtime
                try:
                    owner_pid = int(LOCK_FILE.read_text(encoding="ascii").strip())
                    os.kill(owner_pid, 0)
                    owner_alive = True
                except (ValueError, ProcessLookupError):
                    owner_alive = False
                except PermissionError:
                    owner_alive = True
                except OSError:
                    owner_alive = age <= 120
                if age > 120 and not owner_alive:
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


def _strict_json_loads(source):
    """Parse JSON without duplicate object keys or non-standard constants."""
    def reject_constant(value):
        raise ValueError(f"Constante JSON no estándar: {value}")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Clave JSON duplicada: {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(source, parse_constant=reject_constant, object_pairs_hook=reject_duplicates)
    except RecursionError as exc:
        raise ValueError("El JSON supera el límite de anidamiento") from exc


def _read_registry():
    if not REGISTRY_FILE.exists():
        return _empty_registry()
    try:
        if REGISTRY_FILE.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("el registro supera 5 MiB")
        with REGISTRY_FILE.open("r", encoding="utf-8") as stream:
            registry = _strict_json_loads(stream.read())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
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
    schema_version = registry.get("schema_version", REGISTRY_VERSION)
    if not isinstance(schema_version, int) or schema_version > REGISTRY_VERSION or schema_version < 1:
        raise RuntimeError(f"Versión de esquema de registro no compatible: {schema_version!r}")
    for name, metadata in registry["packages"].items():
        try:
            _validate_name(name)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("El registro contiene un nombre de paquete no válido") from exc
        if not isinstance(metadata, dict):
            raise RuntimeError(f"Los metadatos del paquete {name!r} no son válidos")
        if "version" in metadata:
            try:
                _parse_version(metadata["version"])
            except ValueError as exc:
                raise RuntimeError(f"La versión registrada para {name!r} no es válida") from exc
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
        if REGISTRY_FILE.exists():
            backup = REGISTRY_FILE.with_suffix(".json.bak")
            shutil.copy2(REGISTRY_FILE, backup)
        os.replace(temp_name, REGISTRY_FILE)
        if os.name != "nt":
            try:
                os.chmod(REGISTRY_FILE, 0o600)
            except OSError:
                pass
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not PACKAGE_NAME_RE.fullmatch(name):
        raise ValueError("El nombre debe empezar por letra o _ y contener solo letras, números y _ (máx. 64)")
    if name.casefold() in WINDOWS_RESERVED_NAMES:
        raise ValueError("El nombre coincide con un nombre de dispositivo reservado")
    return name


def _parse_version(value):
    match = PACKAGE_VERSION_RE.fullmatch(str(value))
    if not match:
        raise ValueError(f"Versión semántica no válida: {value!r}; usa MAJOR.MINOR.PATCH")
    major, minor, patch, prerelease, build = match.groups()
    for identifier in ((prerelease or "").split(".") if prerelease else ()):
        if not re.fullmatch(r"[0-9A-Za-z-]+", identifier):
            raise ValueError(f"Versión semántica no válida: {value!r}")
        if identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"):
            raise ValueError(f"Identificador numérico prerelease con ceros iniciales: {value!r}")
    for identifier in ((build or "").split(".") if build else ()):
        if not re.fullmatch(r"[0-9A-Za-z-]+", identifier):
            raise ValueError(f"Versión semántica no válida: {value!r}")
    return int(major), int(minor), int(patch), prerelease


def _version_sort_key(value):
    major, minor, patch, prerelease = _parse_version(value)
    identifiers = tuple(
        (0, int(item)) if item.isdigit() else (1, item)
        for item in prerelease.split(".")
    ) if prerelease else ()
    return major, minor, patch, 0 if prerelease else 1, identifiers


def _version_precedence(value):
    major, minor, patch, prerelease = _parse_version(value)
    identifiers = tuple(
        (0, int(item)) if item.isdigit() else (1, item)
        for item in prerelease.split(".")
    ) if prerelease else ()
    return major, minor, patch, 0 if prerelease else 1, identifiers


def _version_satisfies(version, requirement):
    actual = _parse_version(version)
    requirement = str(requirement).strip()
    if requirement in ("", "*"):
        return True
    match = re.fullmatch(r"(\^|~|>=)?\s*(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)", requirement)
    if not match:
        raise ValueError(f"Restricción de versión no admitida: {requirement!r}")
    operator, expected_text = match.groups()
    expected = _parse_version(expected_text)
    actual_order, expected_order = _version_precedence(version), _version_precedence(expected_text)
    actual_core, expected_core = actual[:3], expected[:3]
    if actual[3] and actual_core != expected_core:
        return False
    if operator == ">=":
        return actual_order >= expected_order
    if operator == "^":
        upper = (expected[0] + 1, 0, 0) if expected[0] else (
            (0, expected[1] + 1, 0) if expected[1] else (0, 0, expected[2] + 1)
        )
        return actual_order >= expected_order and actual_core < upper
    if operator == "~":
        upper = (expected[0], expected[1] + 1, 0)
        return actual_order >= expected_order and actual_core < upper
    return str(version) == expected_text


def _package_file_hashes(package_dir):
    result = {}
    for item in sorted(path for path in package_dir.rglob("*") if path.is_file()):
        relative = item.relative_to(package_dir).as_posix()
        result[relative] = _sha256(item)
    return result


def _verify_manifest_file_map(declared_files, actual_files):
    if not isinstance(declared_files, dict) or not declared_files or len(declared_files) > MAX_PACKAGE_FILES:
        raise ValueError("Un paquete firmado requiere files como objeto con hashes SHA-256")
    expected = {}
    for name, digest in declared_files.items():
        if (not isinstance(name, str) or "\\" in name or not re.fullmatch(r"[0-9a-fA-F]{64}", str(digest))):
            raise ValueError(f"Entrada no válida en files del manifiesto: {name!r}")
        relative = PurePosixPath(name)
        if relative.is_absolute() or not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
            raise ValueError(f"Ruta no segura en files del manifiesto: {name!r}")
        normalized = unicodedata.normalize("NFC", relative.as_posix())
        if normalized != name:
            raise ValueError(f"La ruta del manifiesto debe estar normalizada: {name!r}")
        if normalized in expected:
            raise ValueError(f"Ruta duplicada en files del manifiesto: {name!r}")
        expected[normalized] = str(digest).lower()
    actual = {}
    for name, digest in actual_files.items():
        normalized = unicodedata.normalize("NFC", name)
        if normalized in actual:
            raise ValueError(f"El paquete contiene rutas Unicode duplicadas: {normalized!r}")
        actual[normalized] = digest
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(name for name in set(expected) & set(actual) if expected[name] != actual[name])
        details = missing[:5] + extra[:5] + changed[:5]
        raise ValueError(f"Los hashes files del manifiesto no coinciden: {', '.join(details)}")
    return actual


def _load_trust_store(filename=None):
    path_value = (filename or os.environ.get("MYR_PACKAGE_TRUST_STORE")
                  or os.environ.get("MUX_PACKAGE_TRUST_STORE"))
    if not path_value:
        return {}
    path = Path(path_value).expanduser()
    if not path.is_file():
        raise ValueError(f"No existe el trust store: {path}")
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("El trust store supera 1 MiB")
    value = _strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ValueError("El trust store debe mapear key_id a clave pública base64")
    return value


def _verify_signed_payload(payload, signature, trust_store, required=False):
    if not signature:
        if required:
            raise ValueError("El paquete requiere una firma Ed25519 de una clave de confianza")
        return False
    if not isinstance(signature, dict) or signature.get("algorithm") != "Ed25519":
        raise ValueError("La firma debe usar el algoritmo Ed25519")
    key_id = signature.get("key_id")
    encoded_signature = signature.get("value")
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", key_id) or not isinstance(encoded_signature, str):
        raise ValueError("El bloque de firma requiere key_id y value")
    encoded_key = trust_store.get(key_id)
    if encoded_key is None:
        raise ValueError(f"La clave de firma {key_id!r} no está en el trust store")
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(encoded_key, validate=True))
        signature_bytes = base64.b64decode(encoded_signature, validate=True)
        unsigned = dict(payload)
        unsigned.pop("signature", None)
        canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        public_key.verify(signature_bytes, canonical)
    except ImportError as exc:
        raise ValueError("Verificar firmas requiere mushyra[crypto]") from exc
    except (ValueError, InvalidSignature) as exc:
        raise ValueError("La firma Ed25519 del paquete no es válida") from exc
    return True


def _canonical_signed_data(document):
    unsigned = dict(document)
    unsigned.pop("signature", None)
    return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_document(filename, private_key_file, key_id):
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", str(key_id)):
        raise ValueError("key_id admite 1..64 letras, números, punto, guion o guion bajo")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise ValueError("Firmar paquetes requiere mushyra[crypto]") from exc
    document_path = Path(filename).expanduser().resolve()
    key_path = Path(private_key_file).expanduser()
    try:
        if document_path.stat().st_size > MAX_REGISTRY_INDEX_BYTES:
            raise ValueError("El documento JSON supera 5 MiB")
        document = _strict_json_loads(document_path.read_text(encoding="utf-8"))
        encoded_key = key_path.read_text(encoding="ascii").strip()
        raw_key = base64.b64decode(encoded_key, validate=True)
        if len(raw_key) != 32:
            raise ValueError("La clave privada Ed25519 debe contener 32 bytes codificados en base64")
        if not isinstance(document, dict):
            raise ValueError("Solo se pueden firmar documentos JSON objeto")
        private_key = Ed25519PrivateKey.from_private_bytes(raw_key)
        document.pop("signature", None)
        signature = private_key.sign(_canonical_signed_data(document))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"No se pudo firmar {document_path}: {exc}") from exc
    document["signature"] = {
        "algorithm": "Ed25519",
        "key_id": str(key_id),
        "value": base64.b64encode(signature).decode("ascii"),
    }
    _atomic_write_json(document_path, document)
    return document["signature"]


def generate_signing_keypair(key_id, private_key_file, trust_store_file):
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", str(key_id)):
        raise ValueError("key_id admite 1..64 letras, números, punto, guion o guion bajo")
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise ValueError("Generar claves requiere mushyra[crypto]") from exc
    private_path = Path(private_key_file).expanduser().resolve()
    trust_path = Path(trust_store_file).expanduser().resolve()
    if private_path == trust_path:
        raise ValueError("La clave privada y el trust store deben usar archivos distintos")
    if private_path.exists():
        raise ValueError(f"No se sobrescribe la clave privada existente: {private_path}")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    trust_path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    raw_private = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    raw_public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if trust_path.exists():
        trust = _load_trust_store(str(trust_path))
    else:
        trust = {}
    if key_id in trust:
        raise ValueError(f"El key_id {key_id!r} ya existe en el trust store")
    descriptor = os.open(str(private_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii", newline="\n") as stream:
        stream.write(base64.b64encode(raw_private).decode("ascii") + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != "nt":
        os.chmod(private_path, 0o600)
    trust[key_id] = base64.b64encode(raw_public).decode("ascii")
    try:
        _atomic_write_json(trust_path, trust)
    except Exception:
        try:
            private_path.unlink()
        except OSError:
            pass
        raise
    return {"private_key": str(private_path), "trust_store": str(trust_path), "key_id": key_id}


def _atomic_write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _validate_public_https(url):
    parsed = urlsplit(str(url))
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("El registro remoto solo admite URL HTTPS sin credenciales")
    try:
        port = parsed.port or 443
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)}
    except (OSError, ValueError) as exc:
        raise ValueError("No se pudo resolver el host HTTPS del paquete") from exc
    if not addresses:
        raise ValueError("El host HTTPS no resolvió ninguna dirección IP")
    for address in addresses:
        try:
            resolved = ipaddress.ip_address(address.split("%", 1)[0])
        except ValueError as exc:
            raise ValueError("El DNS devolvió una dirección IP no válida") from exc
        if not resolved.is_global:
            raise ValueError("El paquete remoto apunta a una dirección privada, local o reservada")
    return parsed


class _PackageRedirectHandler(HTTPRedirectHandler):
    def __init__(self, max_redirects=5):
        super().__init__()
        self.max_redirects = max_redirects
        self.count = 0

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        self.count += 1
        if self.count > self.max_redirects:
            raise ValueError("El registro superó el límite de cinco redirecciones")
        target = urljoin(request.full_url, new_url)
        _validate_public_https(target)
        return super().redirect_request(request, file_pointer, code, message, headers, target)


def _download_https(url, limit, timeout=30):
    _validate_public_https(url)
    request = Request(url, headers={"User-Agent": "Mux-Package-Manager/2"})
    opener = build_opener(_PackageRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        if urlsplit(response.geturl()).scheme.lower() != "https":
            raise ValueError("La descarga fue redirigida fuera de HTTPS")
        length = response.headers.get("Content-Length")
        try:
            if length and int(length) > limit:
                raise ValueError(f"La descarga supera el límite de {limit // (1024 * 1024)} MiB")
        except ValueError as exc:
            if "supera" in str(exc):
                raise
            raise ValueError("Content-Length remoto no válido") from exc
        chunks, total = [], 0
        while True:
            chunk = response.read(min(1024 * 1024, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise ValueError(f"La descarga supera el límite de {limit // (1024 * 1024)} MiB")
        return b"".join(chunks), response.geturl()


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
        if member.file_size > 20 * 1024 * 1024 or total_size > MAX_PACKAGE_BYTES:
            raise ValueError("El ZIP supera el límite de 20 MB por archivo o 100 MB total")
        if member.flag_bits & 0x1:
            raise ValueError(f"No se admiten entradas cifradas en ZIP: {member.filename!r}")
        if member.file_size and (member.compress_size == 0 or member.file_size / member.compress_size > 1000):
            raise ValueError(f"La razón de compresión ZIP supera 1000:1 en {member.filename!r}")
        raw = member.filename
        if "\\" in raw:
            raise ValueError(f"Ruta no válida en ZIP: {raw!r}")
        relative = PurePosixPath(raw)
        if relative.is_absolute() or not relative.parts or any(part in ("..", "") for part in relative.parts):
            raise ValueError(f"Ruta no segura en ZIP: {raw!r}")
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError(f"No se permiten enlaces simbólicos en ZIP: {raw!r}")
        file_type = stat.S_IFMT(mode)
        if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError(f"No se permiten archivos especiales en ZIP: {raw!r}")
        if any(":" in part for part in relative.parts):
            raise ValueError(f"Ruta absoluta no permitida en ZIP: {raw!r}")
        for part in relative.parts:
            if part.split(".", 1)[0].casefold() in WINDOWS_RESERVED_NAMES:
                raise ValueError(f"Nombre reservado no permitido en ZIP: {raw!r}")
        normalized_name = unicodedata.normalize("NFC", relative.as_posix()).casefold().rstrip("/")
        if normalized_name in seen_paths:
            raise ValueError(f"Ruta duplicada en ZIP: {raw!r}")
        seen_paths.add(normalized_name)
        target = destination.joinpath(*relative.parts)
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if target.suffix.lower() not in (".myr", ".mux", ".json", ".md", ".txt"):
            raise ValueError(f"Tipo de archivo no permitido en paquete MUSHYRA: {raw!r}")
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
        payload, _final_url = _download_https(source, MAX_ARCHIVE_BYTES)
        filename.write_bytes(payload)
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

    original_path = Path(source).expanduser()
    if original_path.is_symlink():
        raise ValueError(f"No se admiten enlaces simbólicos como origen: {original_path}")
    path = original_path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"No existe el origen {source!r}; usa una ruta local o una URL HTTPS con --sha256")
    if path.is_file() and path.suffix.lower() in (".myr", ".mux"):
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("El archivo MUSHYRA supera el límite de 20 MiB")
        package_dir = staging / "package"
        package_dir.mkdir()
        shutil.copy2(path, package_dir / path.name)
        actual = _sha256(path)
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise ValueError("SHA-256 no coincide con el archivo MUSHYRA")
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
            if item.is_file() and item.suffix.lower() in (".myr", ".mux", ".json", ".md", ".txt"):
                copied_files += 1
                file_size = item.stat().st_size
                copied_bytes += file_size
                if file_size > 20 * 1024 * 1024:
                    raise ValueError(f"El archivo {item.name!r} supera el límite de 20 MiB")
                if copied_files > MAX_PACKAGE_FILES or copied_bytes > MAX_PACKAGE_BYTES:
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
            relative = item.relative_to(package_dir).as_posix().encode("utf-8")
            contents = item.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(contents).to_bytes(8, "big"))
            digest.update(contents)
        actual = digest.hexdigest()
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise ValueError("SHA-256 del contenido de la carpeta no coincide")
        return actual, str(path)
    raise ValueError("El origen debe ser una carpeta, un archivo .myr/.mux, un ZIP o una URL HTTPS")


def package_file_hashes(directory):
    """Return hashes to place in a signed manifest's ``files`` field."""
    source = Path(directory).expanduser().resolve()
    if not source.is_dir():
        raise ValueError("mux-pkg hashes requiere una carpeta de paquete")
    with tempfile.TemporaryDirectory(prefix="mux-package-hashes-") as temporary:
        staging = Path(temporary)
        _stage_source(str(source), staging)
        return {
            name: digest for name, digest in _package_file_hashes(staging / "package").items()
            if name != "mux-package.json"
        }


def create_package_archive(directory, output_path):
    """Create a sorted ZIP with normalized timestamps and safe file types."""
    source = Path(directory).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve()
    if destination.suffix.lower() != ".zip":
        raise ValueError("El archivo de salida debe terminar en .zip")
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise ValueError("El ZIP de salida debe quedar fuera de la carpeta del paquete")
    if not source.is_dir():
        raise ValueError("mux-pkg pack requiere una carpeta de paquete")
    with tempfile.TemporaryDirectory(prefix="mux-package-pack-") as temporary:
        staging = Path(temporary)
        _stage_source(str(source), staging)
        package_dir = staging / "package"
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_zip = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
        os.close(descriptor)
        try:
            with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for item in sorted(path for path in package_dir.rglob("*") if path.is_file()):
                    relative = item.relative_to(package_dir).as_posix()
                    info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    archive.writestr(info, item.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            if Path(temporary_zip).stat().st_size > MAX_ARCHIVE_BYTES:
                raise ValueError("El ZIP generado supera el límite de 50 MiB")
            os.replace(temporary_zip, destination)
        finally:
            try:
                os.unlink(temporary_zip)
            except FileNotFoundError:
                pass
    return _sha256(destination)


def _prepare_entrypoint(package_dir: Path, package_name: str):
    manifest_path = package_dir / "mux-package.json"
    manifest = {}
    if manifest_path.is_file():
        try:
            if manifest_path.stat().st_size > 1024 * 1024:
                raise ValueError("mux-package.json supera 1 MiB")
            manifest = _strict_json_loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"mux-package.json no válido: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ValueError("mux-package.json debe contener un objeto JSON")
    name = _validate_name(str(manifest.get("name", package_name)))
    version = str(manifest.get("version", "0.0.0"))
    _parse_version(version)
    description = str(manifest.get("description", ""))
    if len(description) > 4096:
        raise ValueError("La descripción del paquete supera 4096 caracteres")
    dependencies = manifest.get("dependencies", {})
    if not isinstance(dependencies, dict) or len(dependencies) > 256:
        raise ValueError("dependencies debe ser un objeto con un máximo de 256 paquetes")
    for dependency, requirement in dependencies.items():
        _validate_name(dependency)
        _parse_version("0.0.0") if requirement in ("", "*") else _version_satisfies("0.0.0", requirement)
    main = manifest.get("main")
    if main:
        main_path = (package_dir / str(main)).resolve()
        if (package_dir.resolve() not in main_path.parents
                or main_path.suffix.lower() not in (".myr", ".mux") or not main_path.is_file()):
            raise ValueError("El campo main debe apuntar a un archivo .myr o .mux dentro del paquete")
    else:
        expected = [package_dir / f"{name}.myr", package_dir / f"{name}.mux"]
        source_files = sorted(
            [*package_dir.rglob("*.myr"), *package_dir.rglob("*.mux")],
            key=lambda item: (item.suffix.lower() != ".myr", item.as_posix().casefold()),
        )
        expected_file = next((item for item in expected if item.is_file()), None)
        if expected_file is not None:
            main_path = expected_file
        elif len(source_files) == 1:
            main_path = source_files[0]
        else:
            raise ValueError("Define 'main' en mux-package.json o incluye un único archivo .myr/.mux de entrada")
    target = package_dir / f"{name}{main_path.suffix.lower()}"
    if main_path != target:
        shutil.copy2(main_path, target)
    return name, manifest


def _check_dependencies(manifest, registry, package_name):
    if not isinstance(manifest, dict) or not isinstance(manifest.get("dependencies", {}), dict):
        raise ValueError("dependencies debe ser un objeto JSON")
    dependencies = manifest.get("dependencies", {})
    if len(dependencies) > 256:
        raise ValueError("dependencies admite un máximo de 256 paquetes")
    for dependency, requirement in dependencies.items():
        _validate_name(dependency)
        if not isinstance(requirement, str):
            raise ValueError(f"La restricción de versión de {dependency!r} debe ser texto")
        if dependency == package_name:
            raise ValueError(f"El paquete {package_name!r} no puede depender de sí mismo")
        installed = registry.get(dependency)
        if installed is None:
            raise ValueError(f"Falta la dependencia {dependency!r} ({requirement}); instálala antes")
        if not _version_satisfies(installed.get("version", "0.0.0"), requirement):
            raise ValueError(
                f"La dependencia {dependency!r} requiere {requirement}, pero está instalada la versión {installed.get('version')}"
            )


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
    print("Paquetes MUSHYRA instalados:\n")
    for name, info in sorted(packages.items()):
        print(f"  {name} ({info.get('version', 'sin versión')})")
        print(f"    {info.get('description', 'Sin descripción')}")
        print(f"    {info.get('installed_at', 'fecha desconocida')}\n")
    return packages


def install_package(source: str, name: str = None, sha256: str = None,
                    trusted_keys_file=None, require_signature=None,
                    expected_version=None, registry_index_verified=False):
    init_package_system()
    is_remote = urlsplit(source).scheme.lower() == "https"
    if is_remote and not name:
        raise ValueError("Las URL HTTPS requieren --name para definir el nombre del módulo")
    if require_signature is None:
        require_signature = is_remote
    source_path = Path(source).expanduser()
    inferred_name = source_path.stem if source_path.is_file() else source_path.name
    package_name = _validate_name(name or inferred_name)
    with tempfile.TemporaryDirectory(prefix="mux-package-") as temp_name:
        staging_root = Path(temp_name)
        digest, source_label = _stage_source(source, staging_root, sha256)
        package_dir = staging_root / "package"
        if not package_dir.is_dir():
            raise ValueError("El paquete no contiene archivos")
        source_file_hashes = {
            name: value for name, value in _package_file_hashes(package_dir).items()
            if name != "mux-package.json"
        }
        manifest_name, manifest = _prepare_entrypoint(package_dir, package_name)
        if name and manifest_name != name:
            raise ValueError(f"El nombre del manifiesto ({manifest_name}) no coincide con --name ({name})")
        package_name = _validate_name(manifest_name)
        manifest_version = str(manifest.get("version", "0.0.0"))
        if expected_version is not None and manifest_version != expected_version:
            raise ValueError("La versión del manifiesto del paquete no coincide con el índice firmado")
        trusted_keys = _load_trust_store(trusted_keys_file)
        signature_verified = _verify_signed_payload(
            manifest, manifest.get("signature"), trusted_keys, required=require_signature
        )
        if require_signature and signature_verified:
            # Check the original payload before _prepare_entrypoint may create
            # a canonical import filename for the installed module.
            _verify_manifest_file_map(manifest.get("files"), source_file_hashes)
        files = sorted(item.relative_to(package_dir).as_posix() for item in package_dir.rglob("*") if item.is_file())
        if not any(item.endswith((".myr", ".mux")) for item in files):
            raise ValueError("El paquete debe incluir al menos un archivo .myr o .mux")

        target = PACKAGES_DIR / package_name
        install_stage = staging_root / "ready"
        shutil.copytree(package_dir, install_stage)
        metadata = {
            "version": manifest_version,
            "description": str(manifest.get("description", f"Módulo Mux {package_name}")),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": source_label,
            "sha256": digest,
            "files": files,
            "file_hashes": _package_file_hashes(package_dir),
            "dependencies": manifest.get("dependencies", {}),
            "signature_verified": signature_verified,
            "registry_index_verified": bool(registry_index_verified),
            "install_path": str(target),
        }
        backup = staging_root / "previous"
        with _registry_lock():
            registry = _read_registry()
            _check_dependencies(manifest, registry["packages"], package_name)
            colliding = [entry for entry in registry["packages"] if entry.casefold() == package_name.casefold() and entry != package_name]
            if colliding:
                raise ValueError(f"El paquete {package_name!r} colisiona por mayúsculas con {colliding[0]!r}")
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


def verify_package(package_name: str):
    init_package_system()
    package_name = _validate_name(package_name)
    registry = _read_registry()["packages"]
    metadata = registry.get(package_name)
    if metadata is None:
        raise ValueError(f"El paquete {package_name!r} no está instalado")
    target = (PACKAGES_DIR / package_name).resolve()
    if target.parent != PACKAGES_DIR.resolve() or not target.is_dir():
        raise ValueError(f"No se encuentra el directorio instalado de {package_name!r}")
    expected = metadata.get("file_hashes")
    if not isinstance(expected, dict) or not expected:
        raise ValueError(f"El registro de {package_name!r} no contiene hashes por archivo; vuelve a instalarlo")
    for item in target.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"El paquete contiene un enlace simbólico inesperado: {item.relative_to(target)}")
    actual_files = _package_file_hashes(target)
    if actual_files != expected:
        changed = sorted(set(actual_files) ^ set(expected))
        changed.extend(sorted(name for name in set(actual_files) & set(expected) if actual_files[name] != expected[name]))
        raise ValueError(f"Los archivos de {package_name!r} cambiaron: {', '.join(changed[:20])}")
    return True


def audit_packages():
    packages = _read_registry()["packages"]
    results = {}
    for package_name in sorted(packages):
        try:
            verify_package(package_name)
            results[package_name] = {"ok": True, "message": "integridad correcta"}
        except (OSError, ValueError, RuntimeError) as exc:
            results[package_name] = {"ok": False, "message": str(exc)}
    return results


def _load_registry_index(registry_source=None, trusted_keys_file=None):
    source = registry_source or os.environ.get("MYR_PACKAGE_REGISTRY") or os.environ.get("MUX_PACKAGE_REGISTRY")
    if not source:
        raise ValueError("Configura MYR_PACKAGE_REGISTRY con un índice local o una URL HTTPS firmada")
    parsed = urlsplit(str(source))
    remote = parsed.scheme.lower() in ("http", "https")
    if remote and parsed.scheme.lower() != "https":
        raise ValueError("El índice remoto solo admite HTTPS")
    if remote:
        payload, _ = _download_https(str(source), MAX_REGISTRY_INDEX_BYTES)
    else:
        path = Path(source).expanduser()
        if path.stat().st_size > MAX_REGISTRY_INDEX_BYTES:
            raise ValueError("El índice del registro supera 5 MiB")
        payload = path.read_bytes()
    try:
        index = _strict_json_loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Índice de paquetes JSON no válido: {exc}") from exc
    if not isinstance(index, dict) or index.get("schema_version") != 1 or not isinstance(index.get("packages"), list):
        raise ValueError("El índice debe usar schema_version=1 y contener packages como lista")
    signature_verified = _verify_signed_payload(
        index, index.get("signature"), _load_trust_store(trusted_keys_file), required=remote
    )
    seen_versions = set()
    for entry in index["packages"]:
        if not isinstance(entry, dict):
            raise ValueError("El índice contiene una entrada de paquete no válida")
        _validate_name(entry.get("name"))
        _parse_version(entry.get("version"))
        package_version = (entry["name"].casefold(), entry["version"])
        if package_version in seen_versions:
            raise ValueError(f"El índice repite {entry['name']} {entry['version']}")
        seen_versions.add(package_version)
        if len(str(entry.get("description", ""))) > 4096:
            raise ValueError("La descripción de un paquete supera 4096 caracteres")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(entry.get("sha256", ""))):
            raise ValueError("Cada entrada del índice requiere un SHA-256 de 64 caracteres")
        _validate_public_https(entry.get("url", ""))
    return index, signature_verified


def search_packages(query="", registry_source=None, trusted_keys_file=None):
    index, _verified = _load_registry_index(registry_source, trusted_keys_file)
    needle = str(query).casefold()
    results = [entry for entry in index["packages"]
               if needle in entry["name"].casefold() or needle in str(entry.get("description", "")).casefold()]
    return sorted(results, key=lambda entry: (entry["name"].casefold(), _version_sort_key(entry["version"])))


def _select_registry_package(name, version=None, registry_source=None, trusted_keys_file=None):
    index, index_verified = _load_registry_index(registry_source, trusted_keys_file)
    entries = [entry for entry in index["packages"] if entry["name"].casefold() == str(name).casefold()]
    if version is not None:
        entries = [entry for entry in entries if entry["version"] == version]
    if not entries:
        raise ValueError(f"No se encontró {name!r}" + (f" versión {version}" if version else "") + " en el registro")
    entry = max(entries, key=lambda item: _version_sort_key(item["version"]))
    return entry, index_verified


def install_from_registry(name, version=None, registry_source=None, trusted_keys_file=None):
    entry, index_verified = _select_registry_package(name, version, registry_source, trusted_keys_file)
    metadata = install_package(
        entry["url"], name=entry["name"], sha256=entry["sha256"],
        trusted_keys_file=trusted_keys_file, require_signature=True,
        expected_version=entry["version"], registry_index_verified=index_verified,
    )
    return metadata


def create_lockfile(manifest_path="mux-package.json", output_path="mux.lock.json"):
    manifest_file = Path(manifest_path).expanduser().resolve()
    try:
        if manifest_file.stat().st_size > 1024 * 1024:
            raise ValueError("El manifiesto supera 1 MiB")
        manifest = _strict_json_loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer el manifiesto {manifest_file}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("El manifiesto debe ser un objeto JSON")
    registry = _read_registry()["packages"]
    _check_dependencies(manifest, registry, manifest.get("name", ""))
    packages = {}
    visiting = set()

    def resolve(name, requirement):
        if name in visiting:
            raise ValueError(f"Ciclo de dependencias detectado al bloquear {name!r}")
        info = registry.get(name)
        if info is None:
            raise ValueError(f"Falta la dependencia {name!r}")
        if not _version_satisfies(info.get("version", "0.0.0"), requirement):
            raise ValueError(f"{name!r} no satisface la versión requerida {requirement}")
        if name in packages:
            if packages[name]["version"] != info["version"]:
                raise ValueError(f"Se requieren dos versiones incompatibles de {name!r}")
            return
        visiting.add(name)
        for child, child_requirement in sorted(info.get("dependencies", {}).items()):
            resolve(child, child_requirement)
        visiting.remove(name)
        packages[name] = {
            "version": info["version"],
            "sha256": info.get("sha256"),
            "source": info.get("source"),
            "dependencies": info.get("dependencies", {}),
        }

    for name, requirement in sorted(manifest.get("dependencies", {}).items()):
        resolve(name, requirement)
    lock = {"lock_version": 1, "root": manifest.get("name"), "packages": packages}
    destination = Path(output_path).expanduser().resolve()
    serialized = json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return lock


def install_lockfile(lockfile="mux.lock.json", trusted_keys_file=None):
    path = Path(lockfile).expanduser().resolve()
    try:
        if path.stat().st_size > MAX_REGISTRY_INDEX_BYTES:
            raise ValueError("El lockfile supera 5 MiB")
        lock = _strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer el lockfile {path}: {exc}") from exc
    if not isinstance(lock, dict) or lock.get("lock_version") != 1 or not isinstance(lock.get("packages"), dict):
        raise ValueError("El lockfile debe usar lock_version=1 y contener packages como objeto")

    packages = lock["packages"]
    order, visiting, visited = [], set(), set()

    def visit(name):
        if name in visiting:
            raise ValueError(f"Ciclo de dependencias en el lockfile: {name!r}")
        if name in visited:
            return
        entry = packages.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"Entrada no válida en el lockfile: {name!r}")
        _validate_name(name)
        _parse_version(entry.get("version"))
        source = entry.get("source")
        if not isinstance(source, str) or not source:
            raise ValueError(f"Falta source para {name!r} en el lockfile")
        digest = entry.get("sha256")
        if digest is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(digest)):
            raise ValueError(f"SHA-256 no válido para {name!r} en el lockfile")
        dependencies = entry.get("dependencies", {})
        if not isinstance(dependencies, dict):
            raise ValueError(f"dependencies no válido para {name!r} en el lockfile")
        visiting.add(name)
        for dependency, requirement in sorted(dependencies.items()):
            _validate_name(dependency)
            if dependency not in packages:
                raise ValueError(f"Falta {dependency!r} en el lockfile")
            dependency_entry = packages[dependency]
            if not isinstance(dependency_entry, dict):
                raise ValueError(f"Entrada no válida en el lockfile: {dependency!r}")
            if not isinstance(requirement, str) or not _version_satisfies(dependency_entry.get("version"), requirement):
                raise ValueError(f"La versión fijada de {dependency!r} no satisface {requirement!r}")
            visit(dependency)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for package_name in sorted(packages):
        visit(package_name)
    installed = []
    for package_name in order:
        entry = packages[package_name]
        source = entry["source"]
        remote = urlsplit(source).scheme.lower() == "https"
        if remote and not entry.get("sha256"):
            raise ValueError(f"Falta SHA-256 para el paquete remoto {package_name!r}")
        install_package(
            source, name=package_name, sha256=entry.get("sha256"),
            trusted_keys_file=trusted_keys_file,
            require_signature=True if remote else False,
            expected_version=entry["version"],
        )
        installed.append(package_name)
    return installed


def outdated_packages(registry_source=None, trusted_keys_file=None):
    installed = _read_registry()["packages"]
    index, _ = _load_registry_index(registry_source, trusted_keys_file)
    latest = {}
    for entry in index["packages"]:
        name = entry["name"]
        if name not in latest or _version_sort_key(entry["version"]) > _version_sort_key(latest[name]["version"]):
            latest[name] = entry
    return {name: {"installed": metadata.get("version", "0.0.0"), "latest": latest[name]["version"]}
            for name, metadata in installed.items()
            if name in latest and _version_sort_key(latest[name]["version"]) > _version_sort_key(metadata.get("version", "0.0.0"))}


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
    parser = argparse.ArgumentParser(prog="myr-pkg", description="Administra paquetes MUSHYRA locales y firmados")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="Lista paquetes instalados")
    list_parser.add_argument("--json", action="store_true", help="Imprime el registro como JSON")
    install_parser = subparsers.add_parser("install", help="Instala un paquete local o del registro")
    install_parser.add_argument("source", nargs="?", help="Ruta local, URL HTTPS o nombre si se usa --from-registry")
    install_parser.add_argument("--name", help="Nombre de importación del paquete")
    install_parser.add_argument("--sha256", help="Hash SHA-256 obligatorio para una URL HTTPS")
    install_parser.add_argument("--from-registry", action="store_true", help="Interpreta source como nombre del paquete")
    install_parser.add_argument("--registry", help="Ruta o URL HTTPS del índice del registro")
    install_parser.add_argument("--version", help="Versión exacta a instalar desde el registro")
    install_parser.add_argument("--trust-store", help="JSON de confianza que mapea key_id a clave Ed25519 base64")
    install_parser.add_argument("--allow-unsigned", action="store_true", help="Permite un ZIP HTTPS sin firma Ed25519; solo comprueba SHA-256")
    remove_parser = subparsers.add_parser("remove", aliases=["uninstall"], help="Desinstala un paquete")
    remove_parser.add_argument("name")
    search_parser = subparsers.add_parser("search", help="Busca en el registro configurado")
    search_parser.add_argument("query", nargs="?", default="")
    search_parser.add_argument("--registry")
    search_parser.add_argument("--trust-store")
    search_parser.add_argument("--json", action="store_true")
    update_parser = subparsers.add_parser("update", help="Actualiza un paquete desde el registro firmado")
    update_parser.add_argument("name")
    update_parser.add_argument("--version")
    update_parser.add_argument("--registry")
    update_parser.add_argument("--trust-store")
    verify_parser = subparsers.add_parser("verify", help="Comprueba los hashes de paquetes instalados")
    verify_parser.add_argument("name", nargs="?")
    verify_parser.add_argument("--json", action="store_true")
    lock_parser = subparsers.add_parser("lock", help="Genera un lockfile desde mux-package.json y paquetes instalados")
    lock_parser.add_argument("--manifest", default="mux-package.json")
    lock_parser.add_argument("--output", default="mux.lock.json")
    locked_parser = subparsers.add_parser("install-lock", help="Instala las versiones y hashes fijados en un lockfile")
    locked_parser.add_argument("--file", default="mux.lock.json")
    locked_parser.add_argument("--trust-store", help="Trust store para verificar firmas de paquetes remotos")
    hashes_parser = subparsers.add_parser("hashes", help="Calcula hashes para el campo files de un manifiesto firmado")
    hashes_parser.add_argument("directory")
    pack_parser = subparsers.add_parser("pack", help="Crea un ZIP ordenado y normalizado de un paquete")
    pack_parser.add_argument("directory")
    pack_parser.add_argument("--output", required=True)
    audit_parser = subparsers.add_parser("audit", help="Comprueba la integridad de todos los paquetes")
    audit_parser.add_argument("--json", action="store_true")
    outdated_parser = subparsers.add_parser("outdated", help="Muestra paquetes con versiones más recientes")
    outdated_parser.add_argument("--registry")
    outdated_parser.add_argument("--trust-store")
    outdated_parser.add_argument("--json", action="store_true")
    sign_parser = subparsers.add_parser("sign", help="Firma un manifiesto o índice JSON con Ed25519")
    sign_parser.add_argument("document")
    sign_parser.add_argument("--private-key", required=True, help="Archivo base64 fuera del repositorio")
    sign_parser.add_argument("--key-id", required=True)
    keygen_parser = subparsers.add_parser("keygen", help="Genera clave Ed25519 y añade su clave pública al trust store")
    keygen_parser.add_argument("key_id")
    keygen_parser.add_argument("--private-key", required=True)
    keygen_parser.add_argument("--trust-store", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            list_packages(args.json)
        elif args.command == "install":
            if args.from_registry:
                if not args.source:
                    parser.error("install --from-registry requiere un nombre de paquete")
                install_from_registry(args.source, args.version, args.registry, args.trust_store)
            elif args.source:
                install_package(args.source, args.name, args.sha256, args.trust_store,
                                require_signature=False if args.allow_unsigned else None)
            else:
                parser.error("indica un origen local/HTTPS o usa --from-registry <nombre>")
        elif args.command == "search":
            results = search_packages(args.query, args.registry, args.trust_store)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for item in results:
                    print(f"{item['name']} {item['version']} — {item.get('description', '')}")
        elif args.command in ("update",):
            install_from_registry(args.name, args.version, args.registry, args.trust_store)
        elif args.command == "verify":
            if args.name:
                results = {args.name: {"ok": verify_package(args.name), "message": "integridad correcta"}}
            else:
                results = audit_packages()
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for name, result in results.items():
                    print(f"{'OK' if result['ok'] else 'ERROR'} {name}: {result['message']}")
            return 0 if all(result["ok"] for result in results.values()) else 1
        elif args.command == "lock":
            lock = create_lockfile(args.manifest, args.output)
            print(f"Lockfile escrito con {len(lock['packages'])} dependencia(s): {args.output}")
        elif args.command == "install-lock":
            installed = install_lockfile(args.file, args.trust_store)
            print(f"Instalados {len(installed)} paquete(s) desde {args.file}")
        elif args.command == "hashes":
            print(json.dumps(package_file_hashes(args.directory), ensure_ascii=False, indent=2, sort_keys=True))
        elif args.command == "pack":
            digest = create_package_archive(args.directory, args.output)
            print(f"ZIP escrito en {args.output}\nSHA-256: {digest}")
        elif args.command == "audit":
            results = audit_packages()
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for name, result in results.items():
                    print(f"{'OK' if result['ok'] else 'ERROR'} {name}: {result['message']}")
            return 0 if all(result["ok"] for result in results.values()) else 1
        elif args.command == "outdated":
            results = outdated_packages(args.registry, args.trust_store)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            elif not results:
                print("Todos los paquetes están actualizados")
            else:
                for name, versions in sorted(results.items()):
                    print(f"{name}: {versions['installed']} -> {versions['latest']}")
        elif args.command == "sign":
            signature = sign_document(args.document, args.private_key, args.key_id)
            print(f"Firma Ed25519 añadida con key_id={signature['key_id']}")
        elif args.command == "keygen":
            result = generate_signing_keypair(args.key_id, args.private_key, args.trust_store)
            print(f"Clave privada protegida en {result['private_key']}")
            print(f"Trust store actualizado en {result['trust_store']}")
        elif args.command in ("remove", "uninstall"):
            if not uninstall_package(args.name):
                return 1
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"myr-pkg: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
