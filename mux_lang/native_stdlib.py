"""Native standard-library modules exposed to Mux programs.

Optional integrations are imported lazily. Every exported function is wrapped
so the interpreter can provide its IO streams, script-relative paths and error
locations consistently.
"""

import base64
import binascii
import hashlib
import hmac
import ipaddress
import json
import math
import os
import random
import re
import secrets
import smtplib
import socket
import sqlite3
import ssl
import time
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .values import ValueSemantics


MAX_HTTP_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_NATIVE_FILE_BYTES = 50 * 1024 * 1024
MAX_MUX_STRING_BYTES = 10 * 1024 * 1024
MAX_DATABASE_RESULT_BYTES = 10 * 1024 * 1024
MAX_JSON_BYTES = 10 * 1024 * 1024
MAX_REGEX_PATTERN_CHARS = 512
MAX_REGEX_INPUT_CHARS = 64 * 1024
MAX_REGEX_RESULTS = 100_000
MAX_REGEX_OUTPUT_CHARS = 10 * 1024 * 1024
MAX_EMAIL_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_DIRECTORY_ENTRIES = 100_000
MAX_NATIVE_SEQUENCE_ITEMS = 1_000_000


def _read_text_bounded(path, encoding="utf-8", limit=MAX_NATIVE_FILE_BYTES):
    if path.stat().st_size > limit:
        raise _error(f"El archivo supera el límite de {limit // (1024 * 1024)} MiB")
    payload = path.read_bytes()
    if len(payload) > limit:
        raise _error(f"El archivo supera el límite de {limit // (1024 * 1024)} MiB")
    try:
        return payload.decode(encoding)
    except (LookupError, UnicodeDecodeError) as exc:
        raise _error(f"No se pudo decodificar el archivo: {exc}") from exc


def _atomic_write_text(path, content, encoding="utf-8"):
    encoded = content.encode(encoding)
    if len(encoded) > MAX_NATIVE_FILE_BYTES:
        raise _error("La escritura supera el límite de 50 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _utf8_length(text, interpreter=None):
    if text.isascii():
        return len(text)
    size = 0
    for index, char in enumerate(text):
        if interpreter is not None and index % 4096 == 0:
            interpreter._tick()
        codepoint = ord(char)
        size += 1 if codepoint < 0x80 else 2 if codepoint < 0x800 else 3 if codepoint < 0x10000 else 4
        if size > MAX_DATABASE_RESULT_BYTES:
            return size
    return size


def _bounded_sql_rows(cursor, max_rows=10_000, interpreter=None):
    rows = []
    result_bytes = 0
    for row in cursor:
        if interpreter is not None:
            interpreter._tick()
        if len(rows) >= max_rows:
            raise _error(f"La consulta supera el límite de {max_rows} filas; pagina los resultados")
        converted = dict(row)
        for key, value in converted.items():
            if interpreter is not None:
                interpreter._tick()
            result_bytes += _utf8_length(str(key), interpreter) + 16
            if isinstance(value, str):
                result_bytes += _utf8_length(value, interpreter)
            elif isinstance(value, (bytes, bytearray, memoryview)):
                result_bytes += len(value)
            else:
                result_bytes += 16
        if result_bytes > MAX_DATABASE_RESULT_BYTES:
            raise _error("El resultado SQLite supera el límite de 10 MiB")
        rows.append(converted)
    return rows


def _strict_json_loads(text):
    def reject_constant(value):
        raise ValueError(f"Constante JSON no estándar: {value}")

    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Clave JSON duplicada: {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(text, parse_constant=reject_constant, object_pairs_hook=reject_duplicate_keys)
    except RecursionError as exc:
        raise ValueError("El JSON supera el límite de anidamiento") from exc


def _validate_http_url(url, allow_private=False):
    parsed = urlparse(str(url))
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise _error("HTTP solo admite URL http(s) absolutas")
    if parsed.username is not None or parsed.password is not None:
        raise _error("No incluyas credenciales dentro de la URL HTTP")
    if allow_private:
        return parsed
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except (OSError, ValueError) as exc:
        raise _error("No se pudo resolver el host HTTP") from exc
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address.split("%", 1)[0])
        except ValueError as exc:
            raise _error("El DNS devolvió una dirección IP no válida") from exc
        if not ip.is_global:
            raise _error("HTTP bloqueó una dirección privada, local o reservada; usa allow_private=true solo si confías en el destino")
    return parsed


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allow_private=False, max_redirects=5):
        super().__init__()
        self.allow_private = allow_private
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise _error(f"HTTP superó el límite de {self.max_redirects} redirecciones")
        target = urljoin(request.full_url, new_url)
        old_scheme = urlparse(request.full_url).scheme.lower()
        parsed = _validate_http_url(target, self.allow_private)
        if old_scheme == "https" and parsed.scheme.lower() != "https":
            raise _error("HTTP bloqueó una redirección de HTTPS a HTTP")
        return super().redirect_request(request, file_pointer, code, message, headers, target)


class NativeFunction:
    """Callable bridge between a Mux interpreter and a Python implementation."""

    def __init__(self, name: str, function: Callable):
        self.name = name
        self.function = function

    def __repr__(self):
        return f"<Mux native function {self.name}>"


def _error(message):
    from .lexer import MuxError
    return MuxError(message)


def _arity(name, args, minimum, maximum=None):
    maximum = minimum if maximum is None else maximum
    if not minimum <= len(args) <= maximum:
        expected = str(minimum) if minimum == maximum else f"{minimum}..{maximum}"
        raise _error(f"{name} requiere {expected} argumento(s); recibió {len(args)}")


def _wrap(name, function):
    return NativeFunction(name, function)


def create_module(name: str, interpreter) -> Dict[str, Any]:
    """Return the public namespace for a built-in Mux module."""

    handler_lock = threading.RLock()

    def call_mux_handler(handler):
        with handler_lock:
            return interpreter.call_value(handler, [])

    async def call_mux_handler_async(handler):
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, call_mux_handler, handler)

    if name == "math":
        def unary(name, fn):
            def call(_vm, *args):
                _arity(name, args, 1)
                try:
                    return fn(args[0])
                except (TypeError, ValueError, OverflowError) as exc:
                    raise _error(f"math.{name}: {exc}") from exc
            return _wrap(name, call)

        def binary(name, fn):
            def call(_vm, *args):
                _arity(name, args, 2)
                try:
                    return fn(args[0], args[1])
                except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
                    raise _error(f"math.{name}: {exc}") from exc
            return _wrap(name, call)

        def sqrt(_vm, *args):
            _arity("sqrt", args, 1)
            try:
                return math.sqrt(args[0])
            except (TypeError, ValueError, OverflowError) as exc:
                raise _error(f"sqrt requiere un número no negativo: {exc}") from exc

        def max_value(_vm, *args):
            _arity("max", args, 1, 10000)
            if len(args) == 1 and not isinstance(args[0], (int, float)):
                try:
                    return max(args[0])
                except (TypeError, ValueError) as exc:
                    raise _error(f"max: {exc}") from exc
            return max(args)

        def min_value(_vm, *args):
            _arity("min", args, 1, 10000)
            if len(args) == 1 and not isinstance(args[0], (int, float)):
                try:
                    return min(args[0])
                except (TypeError, ValueError) as exc:
                    raise _error(f"min: {exc}") from exc
            return min(args)

        return {
            "pi": math.pi,
            "e": math.e,
            "abs": unary("abs", abs),
            "max": _wrap("max", max_value),
            "min": _wrap("min", min_value),
            "pow": binary("pow", pow),
            "sqrt": _wrap("sqrt", sqrt),
            "floor": unary("floor", math.floor),
            "ceil": unary("ceil", math.ceil),
            "round": _wrap("round", lambda _vm, value, digits=0: round(value, digits)),
        }

    if name == "random":
        generator = random.Random()

        def randint(_vm, *args):
            _arity("randint", args, 2)
            try:
                return generator.randint(args[0], args[1])
            except (TypeError, ValueError) as exc:
                raise _error(f"randint: {exc}") from exc

        def random_value(_vm, *args):
            _arity("random", args, 0)
            return generator.random()

        def choice(_vm, *args):
            _arity("choice", args, 1)
            try:
                return generator.choice(args[0])
            except (IndexError, TypeError, KeyError) as exc:
                raise _error(f"choice requiere una colección no vacía: {exc}") from exc

        def shuffle(_vm, *args):
            _arity("shuffle", args, 1)
            if not isinstance(args[0], list):
                raise _error("shuffle requiere una lista")
            generator.shuffle(args[0])
            return args[0]

        def sample(_vm, *args):
            _arity("sample", args, 2)
            try:
                return generator.sample(args[0], args[1])
            except (TypeError, ValueError) as exc:
                raise _error(f"sample: {exc}") from exc

        def seed(_vm, *args):
            _arity("seed", args, 1)
            generator.seed(args[0])
            return True

        return {key: _wrap(key, fn) for key, fn in {
            "randint": randint, "random": random_value, "choice": choice,
            "shuffle": shuffle, "sample": sample, "seed": seed,
        }.items()}

    if name == "sequence":
        from .interpreter import FunctionValue

        def sequence_items(value):
            if not isinstance(value, (list, tuple, str, range, dict)):
                raise _error("Se requiere una lista, tupla, string, range o diccionario")
            try:
                size = len(value)
            except OverflowError as exc:
                raise _error("La secuencia supera el tamaño máximo permitido") from exc
            if size > MAX_NATIVE_SEQUENCE_ITEMS:
                raise _error(f"Una secuencia no puede superar {MAX_NATIVE_SEQUENCE_ITEMS} elementos")
            return value, size

        def snapshot(value):
            value, size = sequence_items(value)
            item_cost = 64 if isinstance(value, str) else 36 if isinstance(value, range) else 8
            interpreter._charge_allocation(48 + item_cost * size)
            items = []
            for item in value:
                interpreter._tick()
                items.append(item)
            return items

        def callback(value):
            if not isinstance(value, (FunctionValue, NativeFunction)):
                raise _error("El primer argumento debe ser una función Mux")
            return value

        def map_values(_vm, *args):
            _arity("sequence.map", args, 2)
            function = callback(args[0])
            items = snapshot(args[1])
            result = []
            for item in items:
                interpreter._tick()
                result.append(interpreter.call_value(function, [item]))
            return result

        def filter_values(_vm, *args):
            _arity("sequence.filter", args, 2)
            function = callback(args[0])
            items = snapshot(args[1])
            result = []
            for item in items:
                interpreter._tick()
                if ValueSemantics.truthy(interpreter.call_value(function, [item])):
                    result.append(item)
            return result

        def enumerate_values(_vm, *args):
            _arity("sequence.enumerate", args, 1, 2)
            start = args[1] if len(args) == 2 else 0
            if not isinstance(start, int) or isinstance(start, bool):
                raise _error("sequence.enumerate requiere un índice entero")
            items, _size = sequence_items(args[0])
            result = []
            for index, item in enumerate(items):
                interpreter._tick()
                result.append((interpreter._guard_value(start + index), item))
            return result

        def zip_values(_vm, *args):
            _arity("sequence.zip", args, 2, 32)
            sources = [sequence_items(value)[0] for value in args]
            result_size = min(map(len, sources))
            result = []
            for index in range(result_size):
                interpreter._tick()
                result.append(tuple(source[index] for source in sources))
            return result

        def any_value(_vm, *args):
            _arity("sequence.any", args, 1)
            items, _size = sequence_items(args[0])
            for item in items:
                interpreter._tick()
                if ValueSemantics.truthy(item):
                    return True
            return False

        def all_value(_vm, *args):
            _arity("sequence.all", args, 1)
            items, _size = sequence_items(args[0])
            for item in items:
                interpreter._tick()
                if not ValueSemantics.truthy(item):
                    return False
            return True

        def sum_values(_vm, *args):
            _arity("sequence.sum", args, 1)
            total = 0
            items, _size = sequence_items(args[0])
            for item in items:
                interpreter._tick()
                if not ValueSemantics.is_number(item):
                    raise _error("sequence.sum solo admite números")
                total = interpreter._guard_value(total + item)
            return total

        return {key: _wrap(f"sequence.{key}", fn) for key, fn in {
            "map": map_values, "filter": filter_values, "enumerate": enumerate_values,
            "zip": zip_values, "any": any_value, "all": all_value, "sum": sum_values,
        }.items()}

    if name == "env":
        def get_value(_vm, *args):
            _arity("get", args, 1, 2)
            value = os.environ.get(str(args[0]))
            return args[1] if value is None and len(args) == 2 else value

        def require_value(_vm, *args):
            _arity("require", args, 1)
            key = str(args[0])
            value = os.environ.get(key)
            if value is None or value == "":
                raise _error(f"Falta la variable de entorno {key!r}")
            return value

        def has_value(_vm, *args):
            _arity("has", args, 1)
            return str(args[0]) in os.environ

        return {key: _wrap(key, fn) for key, fn in {
            "get": get_value, "require": require_value, "has": has_value,
        }.items()}

    if name == "http":
        def request(method, url, data=None, headers=None, timeout=10, allow_private=False):
            _validate_http_url(url, allow_private)
            if headers is not None and not isinstance(headers, dict):
                raise _error("headers debe ser un diccionario")
            request_headers = {}
            for header_name, header_value in (headers or {}).items():
                header_name, header_value = str(header_name), str(header_value)
                if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", header_name) or "\r" in header_value or "\n" in header_value:
                    raise _error("Cabecera HTTP no válida")
                request_headers[header_name] = header_value
            try:
                timeout = float(timeout)
            except (TypeError, ValueError, OverflowError) as exc:
                raise _error("timeout debe ser un número finito mayor que cero") from exc
            if not math.isfinite(timeout) or not 0 < timeout <= 300:
                raise _error("timeout debe ser finito y estar entre 0 y 300 segundos")
            body = None
            if data is not None:
                if isinstance(data, (dict, list)):
                    try:
                        body = json.dumps(data, allow_nan=False).encode("utf-8")
                    except (TypeError, ValueError) as exc:
                        raise _error(f"El cuerpo no se puede serializar como JSON: {exc}") from exc
                    if len(body) > MAX_HTTP_RESPONSE_BYTES:
                        raise _error("El cuerpo HTTP supera el límite de 10 MiB")
                    request_headers.setdefault("Content-Type", "application/json")
                else:
                    body = str(data).encode("utf-8")
                    if len(body) > MAX_HTTP_RESPONSE_BYTES:
                        raise _error("El cuerpo HTTP supera el límite de 10 MiB")
            req = Request(str(url), data=body, headers=request_headers, method=method)
            try:
                opener = build_opener(_SafeRedirectHandler(allow_private))
                with opener.open(req, timeout=timeout) as response:
                    raw = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
                    if len(raw) > MAX_HTTP_RESPONSE_BYTES:
                        raise _error("La respuesta HTTP supera el límite de 10 MiB")
                    charset = response.headers.get_content_charset() or "utf-8"
                    try:
                        text = raw.decode(charset, errors="replace")
                    except LookupError:
                        text = raw.decode("utf-8", errors="replace")
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        payload = None
                    return {"status": response.status, "headers": dict(response.headers.items()),
                            "body": text, "json": payload}
            except HTTPError as exc:
                raw = exc.read(MAX_HTTP_RESPONSE_BYTES + 1)
                if len(raw) > MAX_HTTP_RESPONSE_BYTES:
                    raise _error("La respuesta HTTP supera el límite de 10 MiB")
                charset = exc.headers.get_content_charset() or "utf-8"
                try:
                    text = raw.decode(charset, errors="replace")
                except LookupError:
                    text = raw.decode("utf-8", errors="replace")
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = None
                return {"status": exc.code, "headers": dict(exc.headers.items()),
                        "body": text, "json": payload}
            except (URLError, TimeoutError, OSError, ValueError) as exc:
                detail = "tiempo agotado" if isinstance(exc, TimeoutError) else type(exc).__name__
                raise _error(f"HTTP {method} no completada ({detail})") from exc

        def get(_vm, *args):
            _arity("get", args, 1, 4)
            if len(args) == 4 and not isinstance(args[3], bool):
                raise _error("allow_private debe ser boolean")
            return request("GET", args[0], headers=args[1] if len(args) > 1 else None,
                           timeout=_vm.bounded_timeout(args[2] if len(args) > 2 else 10),
                           allow_private=args[3] if len(args) > 3 else False)

        def post(_vm, *args):
            _arity("post", args, 2, 5)
            if len(args) == 5 and not isinstance(args[4], bool):
                raise _error("allow_private debe ser boolean")
            return request("POST", args[0], args[1],
                           args[2] if len(args) > 2 else None,
                           _vm.bounded_timeout(args[3] if len(args) > 3 else 10),
                           args[4] if len(args) > 4 else False)

        return {"get": _wrap("get", get), "post": _wrap("post", post)}

    if name == "filesystem":
        def path_for(vm, value):
            return vm.resolve_path(value)

        def read(vm, *args):
            _arity("read", args, 1, 2)
            try:
                return _read_text_bounded(path_for(vm, args[0]),
                                          args[1] if len(args) > 1 else "utf-8",
                                          limit=MAX_MUX_STRING_BYTES)
            except OSError as exc:
                raise _error(f"No se pudo leer {args[0]!r}: {exc}") from exc

        def write(vm, *args):
            _arity("write", args, 2, 3)
            try:
                path = path_for(vm, args[0])
                _atomic_write_text(path, str(args[1]), args[2] if len(args) > 2 else "utf-8")
                return True
            except OSError as exc:
                raise _error(f"No se pudo escribir {args[0]!r}: {exc}") from exc

        def append(vm, *args):
            _arity("append", args, 2, 3)
            try:
                path = path_for(vm, args[0])
                encoding = args[2] if len(args) > 2 else "utf-8"
                content = str(args[1])
                current_size = path.stat().st_size if path.exists() else 0
                if current_size + len(content.encode(encoding)) > MAX_NATIVE_FILE_BYTES:
                    raise _error("La escritura supera el límite de 50 MiB")
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding=encoding) as stream:
                    stream.write(content)
                return True
            except OSError as exc:
                raise _error(f"No se pudo añadir a {args[0]!r}: {exc}") from exc

        def exists(vm, *args):
            _arity("exists", args, 1)
            return path_for(vm, args[0]).exists()

        def remove_file(vm, *args):
            _arity("remove_file", args, 1)
            try:
                path_for(vm, args[0]).unlink()
                return True
            except OSError as exc:
                raise _error(f"No se pudo eliminar {args[0]!r}: {exc}") from exc

        def list_dir(vm, *args):
            _arity("list_dir", args, 1)
            try:
                entries = []
                for child in path_for(vm, args[0]).iterdir():
                    if len(entries) >= MAX_DIRECTORY_ENTRIES:
                        raise _error(
                            f"El directorio supera el límite de {MAX_DIRECTORY_ENTRIES} entradas"
                        )
                    entries.append(child.name)
                return sorted(entries)
            except OSError as exc:
                raise _error(f"No se pudo listar {args[0]!r}: {exc}") from exc

        def create_dir(vm, *args):
            _arity("create_dir", args, 1)
            try:
                path_for(vm, args[0]).mkdir(parents=True, exist_ok=True)
                return True
            except OSError as exc:
                raise _error(f"No se pudo crear {args[0]!r}: {exc}") from exc

        def get_size(vm, *args):
            _arity("get_size", args, 1)
            try:
                return path_for(vm, args[0]).stat().st_size
            except OSError as exc:
                raise _error(f"No se pudo consultar {args[0]!r}: {exc}") from exc

        return {key: _wrap(key, fn) for key, fn in {
            "read": read, "write": write, "append": append, "exists": exists,
            "remove_file": remove_file, "list_dir": list_dir,
            "create_dir": create_dir, "get_size": get_size,
        }.items()}

    if name == "json":
        def parse(_vm, *args):
            _arity("parse", args, 1)
            try:
                raw = args[0]
                size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
                if size > MAX_JSON_BYTES:
                    raise ValueError("el documento supera el límite de 10 MiB")
                return _strict_json_loads(raw)
            except (TypeError, ValueError) as exc:
                raise _error(f"JSON no válido: {exc}") from exc

        def stringify(_vm, *args):
            _arity("stringify", args, 1)
            try:
                return json.dumps(args[0], ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            except (TypeError, ValueError, RecursionError) as exc:
                raise _error(f"No se puede serializar JSON: {exc}") from exc

        def pretty(_vm, *args):
            _arity("pretty", args, 1)
            try:
                return json.dumps(args[0], ensure_ascii=False, indent=2, allow_nan=False)
            except (TypeError, ValueError, RecursionError) as exc:
                raise _error(f"No se puede serializar JSON: {exc}") from exc

        def load(vm, *args):
            _arity("load", args, 1)
            path = vm.resolve_path(args[0])
            try:
                return parse(vm, _read_text_bounded(path, limit=MAX_JSON_BYTES))
            except OSError as exc:
                raise _error(f"No se pudo leer JSON {args[0]!r}: {exc}") from exc

        def save(vm, *args):
            _arity("save", args, 2)
            path = vm.resolve_path(args[0])
            try:
                _atomic_write_text(path, pretty(vm, args[1]))
            except OSError as exc:
                raise _error(f"No se pudo guardar JSON {args[0]!r}: {exc}") from exc
            return True

        return {key: _wrap(key, fn) for key, fn in {
            "parse": parse, "stringify": stringify, "pretty": pretty,
            "load": load, "save": save,
        }.items()}

    if name == "crypto":
        def hash_value(algorithm):
            def call(_vm, *args):
                _arity(f"hash_{algorithm}", args, 1)
                return hashlib.new(algorithm, str(args[0]).encode("utf-8")).hexdigest()
            return call

        def encode(_vm, *args):
            _arity("encode_base64", args, 1)
            return base64.b64encode(str(args[0]).encode("utf-8")).decode("ascii")

        def decode(_vm, *args):
            _arity("decode_base64", args, 1)
            try:
                return base64.b64decode(str(args[0]), validate=True).decode("utf-8")
            except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
                raise _error(f"Base64 no válido: {exc}") from exc

        def generate_uuid(_vm, *args):
            _arity("generate_uuid", args, 0)
            return str(uuid.uuid4())

        def generate_token(_vm, *args):
            _arity("generate_token", args, 0, 1)
            length = args[0] if args else 32
            if not isinstance(length, int) or isinstance(length, bool) or not 16 <= length <= 64:
                raise _error("generate_token requiere un tamaño entre 16 y 64 bytes")
            return secrets.token_urlsafe(length)

        def password_hash(_vm, *args):
            _arity("password_hash", args, 1)
            password = str(args[0]).encode("utf-8")
            if not password or len(password) > 4096:
                raise _error("La contraseña debe tener entre 1 y 4096 bytes UTF-8")
            salt = secrets.token_bytes(16)
            try:
                digest = hashlib.scrypt(password, salt=salt, n=16384, r=8, p=1, dklen=32)
            except (AttributeError, ValueError, OSError) as exc:
                raise _error(f"No se pudo derivar el hash scrypt: {exc}") from exc
            encode_part = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
            return f"scrypt$1$16384$8$1${encode_part(salt)}${encode_part(digest)}"

        def password_verify(_vm, *args):
            _arity("password_verify", args, 2)
            password, encoded = str(args[0]).encode("utf-8"), str(args[1])
            if len(password) > 4096 or len(encoded) > 256:
                return False
            try:
                algorithm, version, n, r, p, salt_text, digest_text = encoded.split("$")
                if (algorithm, version, n, r, p) != ("scrypt", "1", "16384", "8", "1"):
                    return False
                decode_part = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
                salt, expected = decode_part(salt_text), decode_part(digest_text)
                if len(salt) != 16 or len(expected) != 32:
                    return False
                actual = hashlib.scrypt(password, salt=salt, n=16384, r=8, p=1, dklen=32)
                return hmac.compare_digest(actual, expected)
            except (ValueError, TypeError, OSError, AttributeError):
                return False

        def cipher_encrypt(_vm, *args):
            _arity("encrypt", args, 2)
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            except ImportError as exc:
                raise _error("encrypt requiere la dependencia opcional 'cryptography'") from exc
            salt, nonce = os.urandom(16), os.urandom(12)
            key = hashlib.pbkdf2_hmac("sha256", str(args[1]).encode("utf-8"), salt, 250000, 32)
            encrypted = AESGCM(key).encrypt(nonce, str(args[0]).encode("utf-8"), None)
            return "v1:" + ":".join(base64.urlsafe_b64encode(v).decode("ascii") for v in (salt, nonce, encrypted))

        def cipher_decrypt(_vm, *args):
            _arity("decrypt", args, 2)
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                version, salt_b64, nonce_b64, payload_b64 = str(args[0]).split(":", 3)
                if version != "v1":
                    raise ValueError("versión no admitida")
                salt, nonce, payload = (base64.urlsafe_b64decode(part) for part in (salt_b64, nonce_b64, payload_b64))
                key = hashlib.pbkdf2_hmac("sha256", str(args[1]).encode("utf-8"), salt, 250000, 32)
                return AESGCM(key).decrypt(nonce, payload, None).decode("utf-8")
            except ImportError as exc:
                raise _error("decrypt requiere la dependencia opcional 'cryptography'") from exc
            except Exception as exc:
                raise _error(f"No se pudo descifrar el texto: {exc}") from exc

        return {"hash_md5": _wrap("hash_md5", hash_value("md5")),
                "hash_sha256": _wrap("hash_sha256", hash_value("sha256")),
                "encode_base64": _wrap("encode_base64", encode),
                "decode_base64": _wrap("decode_base64", decode),
                "generate_uuid": _wrap("generate_uuid", generate_uuid),
                "generate_token": _wrap("generate_token", generate_token),
                "password_hash": _wrap("password_hash", password_hash),
                "password_verify": _wrap("password_verify", password_verify),
                "encrypt": _wrap("encrypt", cipher_encrypt),
                "decrypt": _wrap("decrypt", cipher_decrypt)}

    if name == "regex":
        try:
            import regex as regex_engine
        except ImportError:
            regex_engine = re

        def compile_pattern(pattern):
            pattern = str(pattern)
            if len(pattern) > MAX_REGEX_PATTERN_CHARS:
                raise _error(f"El patrón supera el límite de {MAX_REGEX_PATTERN_CHARS} caracteres")
            if regex_engine is re and (
                re.search(r"\([^)]*[+*][^)]*\)[+*{]", pattern)
                or re.search(r"\([^)]*\|[^)]*\)[+*{]", pattern)
                or re.search(r"\\[1-9]", pattern)
            ):
                raise _error("El patrón contiene cuantificadores ambiguos; instala mux-lang[regex] para límites de tiempo")
            try:
                return regex_engine.compile(pattern)
            except re.error as exc:
                raise _error(f"Expresión regular no válida: {exc}") from exc

        def run_regex(pattern, operation):
            compiled = compile_pattern(pattern)
            try:
                return operation(compiled, 0.1) if regex_engine is not re else operation(compiled, None)
            except TimeoutError as exc:
                raise _error("La expresión regular superó el límite de 100 ms") from exc

        def regex_text(value):
            text = str(value)
            if len(text) > MAX_REGEX_INPUT_CHARS:
                raise _error(f"El texto supera el límite de {MAX_REGEX_INPUT_CHARS} caracteres")
            return text

        def match(_vm, *args):
            _arity("match", args, 2)
            text = regex_text(args[1])
            return run_regex(args[0], lambda pattern, timeout: pattern.search(text, **({"timeout": timeout} if timeout else {})) is not None)

        def find_all(_vm, *args):
            _arity("find_all", args, 2)
            text = regex_text(args[1])
            def collect(pattern, timeout):
                results, output_size = [], 0
                options = {"timeout": timeout} if timeout else {}
                for match in pattern.finditer(text, **options):
                    if len(results) >= MAX_REGEX_RESULTS:
                        raise _error("La expresión regular produjo demasiados resultados")
                    value = match.group(0) if pattern.groups == 0 else (
                        match.group(1) if pattern.groups == 1 else match.groups()
                    )
                    output_size += sum(len(part) for part in value if isinstance(part, str)) if isinstance(value, tuple) else len(value or "")
                    if output_size > MAX_REGEX_OUTPUT_CHARS:
                        raise _error("La salida de la expresión regular supera 10 Mi caracteres")
                    results.append(value)
                return results
            return run_regex(args[0], collect)

        def replace(_vm, *args):
            _arity("replace", args, 3)
            replacement, text = str(args[1]), regex_text(args[2])
            def substitute(pattern, timeout):
                parts, output_size, cursor = [], 0, 0
                options = {"timeout": timeout} if timeout else {}
                for match in pattern.finditer(text, **options):
                    fragment = text[cursor:match.start()]
                    expanded = match.expand(replacement)
                    output_size += len(fragment) + len(expanded)
                    if output_size > MAX_REGEX_OUTPUT_CHARS:
                        raise _error("La salida de la expresión regular supera 10 Mi caracteres")
                    parts.extend((fragment, expanded))
                    cursor = match.end()
                tail = text[cursor:]
                output_size += len(tail)
                if output_size > MAX_REGEX_OUTPUT_CHARS:
                    raise _error("La salida de la expresión regular supera 10 Mi caracteres")
                parts.append(tail)
                return "".join(parts)
            return run_regex(args[0], substitute)

        def split(_vm, *args):
            _arity("split", args, 2)
            text = regex_text(args[1])
            def split_bounded(pattern, timeout):
                results, cursor, previous_end, output_size = [], 0, -1, 0
                options = {"timeout": timeout} if timeout else {}
                for match in pattern.finditer(text, **options):
                    if match.start() == match.end() == previous_end:
                        continue
                    values = [text[cursor:match.start()], *match.groups()]
                    if len(results) + len(values) > MAX_REGEX_RESULTS:
                        raise _error("La expresión regular produjo demasiados resultados")
                    output_size += sum(len(value) for value in values if isinstance(value, str))
                    if output_size > MAX_REGEX_OUTPUT_CHARS:
                        raise _error("La salida de la expresión regular supera 10 Mi caracteres")
                    results.extend(values)
                    cursor, previous_end = match.end(), match.end()
                tail = text[cursor:]
                if len(results) >= MAX_REGEX_RESULTS or output_size + len(tail) > MAX_REGEX_OUTPUT_CHARS:
                    raise _error("La salida de la expresión regular supera el límite configurado")
                results.append(tail)
                return results
            return run_regex(args[0], split_bounded)

        def validate_email(_vm, *args):
            _arity("validate_email", args, 1)
            return re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(args[0])) is not None

        def validate_url(_vm, *args):
            _arity("validate_url", args, 1)
            parsed = urlparse(str(args[0]))
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)

        def validate_phone(_vm, *args):
            _arity("validate_phone", args, 1)
            value = str(args[0])
            return re.fullmatch(r"\+?[0-9][0-9 ()-]{5,24}", value) is not None

        return {key: _wrap(key, fn) for key, fn in {
            "match": match, "find_all": find_all, "replace": replace,
            "split": split, "validate_email": validate_email,
            "validate_url": validate_url, "validate_phone": validate_phone,
            "extract_numbers": lambda _vm, text: re.findall(r"\d+", regex_text(text))[:MAX_REGEX_RESULTS],
            "extract_emails": lambda _vm, text: re.findall(r"[^\s@]+@[^\s@]+\.[^\s@]+", regex_text(text))[:MAX_REGEX_RESULTS],
        }.items()}

    if name == "strings":
        def repeat(_vm, text, count):
            count = _bounded_count(count)
            text = str(text)
            if len(text) * count > 10_000_000:
                raise _error("El resultado de repeat supera el límite de 10 millones de caracteres")
            return text * count

        def pad_left(_vm, text, size, fill=" "):
            return str(text).rjust(_bounded_width(size), str(fill)[:1] or " ")

        def pad_right(_vm, text, size, fill=" "):
            return str(text).ljust(_bounded_width(size), str(fill)[:1] or " ")

        functions = {
            "reverse": lambda _vm, text: str(text)[::-1],
            "capitalize": lambda _vm, text: str(text).capitalize(),
            "count": lambda _vm, text, search: str(text).count(str(search)),
            "starts_with": lambda _vm, text, prefix: str(text).startswith(str(prefix)),
            "ends_with": lambda _vm, text, suffix: str(text).endswith(str(suffix)),
            "contains": lambda _vm, text, search: str(search) in str(text),
            "repeat": repeat,
            "pad_left": pad_left,
            "pad_right": pad_right,
            "trim_left": lambda _vm, text: str(text).lstrip(),
            "trim_right": lambda _vm, text: str(text).rstrip(),
            "to_ascii": lambda _vm, text: [ord(char) for char in str(text)],
            "from_ascii": lambda _vm, values: _from_codepoints(values),
        }
        return {key: _wrap(key, fn) for key, fn in functions.items()}

    if name == "time":
        def sleep(_vm, *args):
            _arity("sleep", args, 1)
            seconds = float(args[0])
            if not math.isfinite(seconds) or not 0 <= seconds <= 300:
                raise _error("sleep requiere segundos finitos entre 0 y 300")
            _vm.sleep(seconds)
            return True

        def now(_vm, *args):
            _arity("now", args, 0)
            return int(time.time())

        def now_utc(_vm, *args):
            _arity("now_utc", args, 0)
            return datetime.now(timezone.utc).isoformat()

        def format_date(_vm, *args):
            _arity("format_date", args, 1, 2)
            try:
                return datetime.fromtimestamp(float(args[0])).strftime(args[1] if len(args) > 1 else "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError, OverflowError, OSError) as exc:
                raise _error(f"Timestamp no válido: {exc}") from exc

        def format_date_utc(_vm, *args):
            _arity("format_date_utc", args, 1, 2)
            try:
                stamp = datetime.fromtimestamp(float(args[0]), timezone.utc)
                return stamp.strftime(args[1] if len(args) > 1 else "%Y-%m-%d %H:%M:%S UTC")
            except (TypeError, ValueError, OverflowError, OSError) as exc:
                raise _error(f"Timestamp no válido: {exc}") from exc

        def current_part(attribute):
            def call(_vm, *args):
                _arity(f"get_{attribute}", args, 0)
                return getattr(datetime.now(), attribute)
            return _wrap(f"get_{attribute}", call)

        def measure_time(vm, *args):
            _arity("measure_time", args, 1)
            start = time.perf_counter()
            vm.call_value(args[0], [])
            return time.perf_counter() - start

        return {"now": _wrap("now", now), "timestamp": _wrap("timestamp", now),
                "now_utc": _wrap("now_utc", now_utc), "format_date_utc": _wrap("format_date_utc", format_date_utc),
                "sleep": _wrap("sleep", sleep), "format_date": _wrap("format_date", format_date),
                "get_year": current_part("year"), "get_month": current_part("month"),
                "get_day": current_part("day"), "get_hour": current_part("hour"),
                "get_minute": current_part("minute"), "get_second": current_part("second"),
                "measure_time": _wrap("measure_time", measure_time)}

    if name == "database":
        state = {"connection": None, "manual_transaction": False}

        def connection():
            if state["connection"] is None:
                raise _error("Conecta primero con connect(ruta)")
            return state["connection"]

        def identifier(value):
            value = str(value)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value):
                raise _error(f"Identificador SQL no válido: {value!r}")
            return '"' + value + '"'

        def where_clause(condition):
            if condition is None or condition == "":
                return "", []
            match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z_0-9]*)\s*(==|=|!=|<=|>=|<|>)\s*(.*?)\s*", str(condition))
            if not match:
                raise _error("Condición SQL no válida; usa campo operador valor")
            field, operator, raw = match.groups()
            operator = "=" if operator == "==" else operator
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
                value = raw[1:-1]
            elif re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", raw):
                value = float(raw) if any(char in raw for char in ".eE") else int(raw)
            else:
                if raw.lower() in ("true", "false"):
                    value = 1 if raw.lower() == "true" else 0
                elif raw.lower() == "null":
                    value = None
                else:
                    value = raw
            if value is None:
                if operator == "=":
                    operator = "IS"
                elif operator == "!=":
                    operator = "IS NOT"
                else:
                    raise _error("null solo admite los operadores = y !=")
            return f" WHERE {identifier(field)} {operator} ?", [value]

        def connect(vm, *args):
            _arity("connect", args, 1, 2)
            path = ":memory:" if str(args[0]) == ":memory:" else vm.resolve_path(args[0])
            timeout = args[1] if len(args) > 1 else 5
            if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 <= timeout <= 60:
                raise _error("El timeout de SQLite debe estar entre 0 y 60 segundos")
            timeout = vm.bounded_timeout(timeout)
            current = None
            try:
                if path != ":memory:":
                    path.parent.mkdir(parents=True, exist_ok=True)
                previous = state["connection"]
                current = sqlite3.connect(str(path), timeout=float(timeout))
                current.row_factory = sqlite3.Row
                current.set_progress_handler(
                    lambda: 1 if ((vm.cancel_event is not None and vm.cancel_event.is_set())
                                  or (vm.budget.deadline is not None
                                      and time.monotonic() >= vm.budget.deadline)) else 0,
                    1000,
                )
                current.execute("PRAGMA foreign_keys = ON")
                current.execute(f"PRAGMA busy_timeout = {int(float(timeout) * 1000)}")
                if path != ":memory:":
                    current.execute("PRAGMA journal_mode = WAL")
                state["connection"] = current
                state["manual_transaction"] = False
                if previous is not None:
                    previous.close()
                return current
            except sqlite3.Error as exc:
                if current is not None:
                    current.close()
                raise _error(f"No se pudo abrir la base de datos: {exc}") from exc

        def finish_write():
            if not state["manual_transaction"]:
                connection().commit()

        def create_table(_vm, *args):
            _arity("create_table", args, 2)
            table, columns = args
            if not isinstance(columns, list) or not columns:
                raise _error("create_table requiere una lista de columnas")
            definitions = []
            for column in columns:
                col = identifier(column)
                kind = "INTEGER PRIMARY KEY AUTOINCREMENT" if str(column).lower() == "id" else "TEXT"
                definitions.append(f"{col} {kind}")
            try:
                connection().execute(f"CREATE TABLE IF NOT EXISTS {identifier(table)} ({', '.join(definitions)})")
                finish_write()
                return True
            except sqlite3.Error as exc:
                raise _error(f"No se pudo crear la tabla: {exc}") from exc

        def insert(_vm, *args):
            _arity("insert", args, 2)
            table, values = args
            if not isinstance(values, dict) or not values:
                raise _error("insert requiere un diccionario de valores")
            columns = list(values)
            query = (f"INSERT INTO {identifier(table)} ({', '.join(identifier(c) for c in columns)}) "
                     f"VALUES ({', '.join('?' for _ in columns)})")
            try:
                cursor = connection().execute(query, [values[c] for c in columns])
                finish_write()
                return cursor.lastrowid
            except sqlite3.Error as exc:
                raise _error(f"No se pudo insertar: {exc}") from exc

        def select(_vm, *args):
            _arity("select", args, 1, 4)
            clause, params = where_clause(args[1] if len(args) > 1 else None)
            limit = args[2] if len(args) > 2 else 10000
            offset = args[3] if len(args) > 3 else 0
            if any(not isinstance(value, int) or isinstance(value, bool) for value in (limit, offset)) or not 1 <= limit <= 10000 or offset < 0:
                raise _error("select requiere limit entre 1 y 10000 y offset no negativo")
            try:
                rows = connection().execute(f"SELECT * FROM {identifier(args[0])}{clause} LIMIT ? OFFSET ?", params + [limit, offset])
                return _bounded_sql_rows(rows, limit, _vm)
            except sqlite3.Error as exc:
                raise _error(f"No se pudo consultar: {exc}") from exc

        def update(_vm, *args):
            _arity("update", args, 3)
            table, values = args[:2]
            if not isinstance(values, dict) or not values:
                raise _error("update requiere un diccionario de valores")
            clause, params = where_clause(args[2])
            if not clause:
                raise _error("update requiere una condición para evitar modificar toda la tabla")
            query = f"UPDATE {identifier(table)} SET " + ", ".join(f"{identifier(c)} = ?" for c in values) + clause
            try:
                cursor = connection().execute(query, list(values.values()) + params)
                finish_write()
                return cursor.rowcount
            except sqlite3.Error as exc:
                raise _error(f"No se pudo actualizar: {exc}") from exc

        def delete(_vm, *args):
            _arity("delete", args, 1, 2)
            clause, params = where_clause(args[1] if len(args) > 1 else None)
            if not clause:
                raise _error("delete requiere una condición para evitar borrar toda la tabla")
            try:
                cursor = connection().execute(f"DELETE FROM {identifier(args[0])}{clause}", params)
                finish_write()
                return cursor.rowcount
            except sqlite3.Error as exc:
                raise _error(f"No se pudo eliminar: {exc}") from exc

        def execute(_vm, *args):
            _arity("execute", args, 1, 2)
            params = args[1] if len(args) > 1 else []
            if not isinstance(params, list):
                raise _error("execute espera los parámetros como lista")
            statement = str(args[0])
            if interpreter.allowed_root is not None:
                scrubbed = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\r\n]*|/\*[\s\S]*?\*/", " ", statement)
                if (re.search(r"\b(?:ATTACH|DETACH|PRAGMA)\b", scrubbed, re.IGNORECASE)
                        or re.search(r"\bVACUUM\b[\s\S]*?\bINTO\b", scrubbed, re.IGNORECASE)):
                    raise _error("execute bloqueó una instrucción SQLite que puede acceder fuera de sandbox_root")
            try:
                cursor = connection().execute(statement, params)
                finish_write()
                if cursor.description:
                    return _bounded_sql_rows(cursor, interpreter=_vm)
                return cursor.rowcount
            except sqlite3.Error as exc:
                raise _error(f"Consulta SQL no válida: {exc}") from exc

        def close(_vm, *args):
            _arity("close", args, 0, 1)
            conn = args[0] if args else state["connection"]
            if conn is not None:
                conn.close()
            state["connection"] = None
            state["manual_transaction"] = False
            return True

        def begin(_vm, *args):
            _arity("begin", args, 0)
            if state["manual_transaction"]:
                raise _error("Ya hay una transacción abierta")
            try:
                connection().execute("BEGIN")
                state["manual_transaction"] = True
                return True
            except sqlite3.Error as exc:
                raise _error(f"No se pudo iniciar la transacción: {exc}") from exc

        def commit(_vm, *args):
            _arity("commit", args, 0)
            try:
                connection().commit()
                state["manual_transaction"] = False
                return True
            except sqlite3.Error as exc:
                raise _error(f"No se pudo confirmar la transacción: {exc}") from exc

        def rollback(_vm, *args):
            _arity("rollback", args, 0)
            try:
                connection().rollback()
                state["manual_transaction"] = False
                return True
            except sqlite3.Error as exc:
                raise _error(f"No se pudo revertir la transacción: {exc}") from exc

        def transaction(vm, *args):
            _arity("transaction", args, 1)
            begin(vm)
            try:
                result = vm.call_value(args[0], [])
                commit(vm)
                return result
            except Exception:
                rollback(vm)
                raise

        return {key: _wrap(key, fn) for key, fn in {
            "connect": connect, "create_table": create_table, "insert": insert,
            "select": select, "update": update, "delete": delete,
            "execute": execute, "close": close, "begin": begin,
            "commit": commit, "rollback": rollback, "transaction": transaction,
        }.items()}

    if name == "email":
        config = {"host": None, "port": None, "username": None, "password": None}

        def configure(_vm, *args):
            _arity("configure_smtp", args, 4)
            if isinstance(args[1], bool):
                raise _error("El puerto SMTP debe ser un entero")
            try:
                port = int(args[1])
            except (TypeError, ValueError, OverflowError) as exc:
                raise _error("El puerto SMTP debe ser un entero") from exc
            if not 1 <= port <= 65535:
                raise _error("El puerto SMTP debe estar entre 1 y 65535")
            host = str(args[0]).strip()
            if not host:
                raise _error("El host SMTP no puede estar vacío")
            config.update(host=host, port=port, username=str(args[2]), password=str(args[3]))
            return True

        def send_mail(vm, recipient, subject, body, html=None, attachment=None):
            if not config["host"]:
                raise _error("Configura SMTP antes de enviar correo")
            message = EmailMessage()
            message["From"] = config["username"]
            message["To"] = str(recipient)
            message["Subject"] = str(subject)
            message.set_content(str(body))
            if html is not None:
                message.add_alternative(str(html), subtype="html")
            if attachment:
                path = vm.resolve_path(attachment)
                try:
                    if path.stat().st_size > MAX_EMAIL_ATTACHMENT_BYTES:
                        raise _error("El adjunto supera el límite de 10 MiB")
                    payload = path.read_bytes()
                    if len(payload) > MAX_EMAIL_ATTACHMENT_BYTES:
                        raise _error("El adjunto supera el límite de 10 MiB")
                except OSError as exc:
                    raise _error(f"No se pudo leer el adjunto: {exc}") from exc
                message.add_attachment(payload, maintype="application", subtype="octet-stream", filename=path.name)
            try:
                if config["port"] == 465:
                    smtp = smtplib.SMTP_SSL(config["host"], config["port"], timeout=vm.bounded_timeout(15), context=ssl.create_default_context())
                else:
                    smtp = smtplib.SMTP(config["host"], config["port"], timeout=vm.bounded_timeout(15))
                with smtp:
                    if config["port"] != 465:
                        smtp.starttls(context=ssl.create_default_context())
                    smtp.login(config["username"], config["password"])
                    smtp.send_message(message)
                return True
            except (OSError, smtplib.SMTPException) as exc:
                raise _error(f"No se pudo enviar el correo: {exc}") from exc

        def send(_vm, *args):
            _arity("send", args, 3)
            return send_mail(_vm, *args)

        def send_html(_vm, *args):
            _arity("send_html", args, 3)
            return send_mail(_vm, args[0], args[1], "Mensaje en formato HTML", html=args[2])

        def send_attachment(_vm, *args):
            _arity("send_with_attachment", args, 4)
            return send_mail(_vm, args[0], args[1], args[2], attachment=args[3])

        return {key: _wrap(key, fn) for key, fn in {
            "configure_smtp": configure, "send": send,
            "send_html": send_html, "send_with_attachment": send_attachment,
        }.items()}

    if name == "console":
        colors = {"black": 30, "red": 31, "green": 32, "yellow": 33,
                  "blue": 34, "magenta": 35, "cyan": 36, "white": 37}

        def styled(text, code):
            value = str(text)
            force = not interpreter.sandbox_mode and "FORCE_COLOR" in os.environ
            enabled = (not interpreter.sandbox_mode and "NO_COLOR" not in os.environ
                       and (force or getattr(interpreter.output, "isatty", lambda: False)()))
            return f"\033[{code}m{value}\033[0m" if enabled else value

        def color(_vm, *args):
            _arity("color", args, 2)
            if str(args[1]).lower() not in colors:
                raise _error(f"Color no admitido: {args[1]}")
            result = styled(args[0], colors[str(args[1]).lower()])
            print(result, file=interpreter.output)
            return result

        def menu(_vm, *args):
            _arity("menu", args, 1)
            if not isinstance(args[0], list) or not args[0]:
                raise _error("menu requiere una lista de opciones no vacía")
            if len(args[0]) > 10_000:
                raise _error("menu no admite más de 10000 opciones")
            for index, item in enumerate(args[0], 1):
                _vm._tick()
                print(f"{index}. {item}", file=interpreter.output)
            try:
                answer = _vm._read_input("Selecciona una opción: ")
            except EOFError as exc:
                raise _error("No hay más entrada disponible") from exc
            try:
                result = int(answer)
            except EOFError as exc:
                raise _error("No hay más entrada disponible") from exc
            except ValueError as exc:
                raise _error("La opción debe ser un número") from exc
            if not 1 <= result <= len(args[0]):
                raise _error("La opción está fuera de rango")
            return result

        def confirm(_vm, *args):
            _arity("confirm", args, 1)
            try:
                answer = _vm._read_input(f"{args[0]} (s/n): ").strip().lower()
            except EOFError as exc:
                raise _error("No hay más entrada disponible") from exc
            return answer in ("s", "si", "sí", "y", "yes")

        def table(_vm, *args):
            _arity("table", args, 1)
            rows = args[0]
            if not isinstance(rows, list) or not rows:
                print("(sin filas)", file=interpreter.output)
                return True
            if len(rows) > 10_000:
                raise _error("table no admite más de 10000 filas")
            columns = []
            seen_columns = set()
            for row in rows:
                _vm._tick()
                if not isinstance(row, dict):
                    raise _error("table requiere una lista de diccionarios")
                for key in row:
                    _vm._tick()
                    if key not in seen_columns:
                        seen_columns.add(key)
                        columns.append(key)
                        if len(columns) > 100:
                            raise _error("table no admite más de 100 columnas")
            widths = {}
            for key in columns:
                width = len(str(key))
                for row in rows:
                    _vm._tick()
                    width = max(width, len(str(row.get(key, ""))))
                widths[key] = width
            print(" | ".join(str(key).ljust(widths[key]) for key in columns), file=interpreter.output)
            print("-+-".join("-" * widths[key] for key in columns), file=interpreter.output)
            for row in rows:
                _vm._tick()
                print(" | ".join(str(row.get(key, "")).ljust(widths[key]) for key in columns), file=interpreter.output)
            return True

        def progress(_vm, *args):
            _arity("progress_bar", args, 2)
            current, total = float(args[0]), float(args[1])
            if not math.isfinite(current) or not math.isfinite(total) or total <= 0:
                raise _error("current debe ser finito y total debe ser positivo y finito")
            ratio = min(max(current / total, 0), 1)
            result = f"[{('=' * int(ratio * 20)).ljust(20)}] {ratio:.0%}"
            print(result, file=interpreter.output)
            return result

        def clear(_vm, *args):
            _arity("clear", args, 0)
            output = interpreter.output
            if getattr(output, "isatty", lambda: False)():
                print("\033[2J\033[H", end="", file=output)
            return True

        functions = {
            "clear": clear,
            "color": color,
            "bold": lambda _vm, text: (print(styled(text, 1), file=interpreter.output), styled(text, 1))[1],
            "italic": lambda _vm, text: (print(styled(text, 3), file=interpreter.output), styled(text, 3))[1],
            "underline": lambda _vm, text: (print(styled(text, 4), file=interpreter.output), styled(text, 4))[1],
            "progress_bar": progress, "table": table, "menu": menu, "confirm": confirm,
            "spinner": lambda _vm, message: (print(f"⏳ {message}", file=interpreter.output), True)[1],
        }
        return {key: _wrap(key, fn) for key, fn in functions.items()}

    if name == "web":
        def require_flask():
            try:
                from flask import Flask
                return Flask
            except ImportError as exc:
                raise _error("El módulo web requiere instalar mux-lang[web]") from exc

        def create_app(_vm, *args):
            _arity("crear_app", args, 0)
            Flask = require_flask()
            return Flask("mux_app")

        def route(_vm, *args):
            _arity("ruta", args, 3)
            app, path, handler = args
            endpoint = f"mux_route_{len(app.url_map._rules)}"
            app.add_url_rule(str(path), endpoint, lambda: interpreter.call_value(handler, []))
            return True

        def run(_vm, *args):
            _arity("iniciar", args, 2)
            if not isinstance(args[1], int) or isinstance(args[1], bool) or not 0 < args[1] < 65536:
                raise _error("El puerto debe estar entre 1 y 65535")
            args[0].run(host="127.0.0.1", port=args[1], debug=False, use_reloader=False)
            return True

        return {"crear_app": _wrap("crear_app", create_app),
                "ruta": _wrap("ruta", route), "iniciar": _wrap("iniciar", run)}

    if name == "discord_bot":
        state = {"tokens": {}}

        def create_bot(_vm, *args):
            _arity("crear_bot", args, 1)
            try:
                import discord
                from discord.ext import commands
            except ImportError as exc:
                raise _error("discord_bot requiere instalar mux-lang[discord]") from exc
            intents = discord.Intents.default()
            intents.message_content = True
            bot = commands.Bot(command_prefix="!", intents=intents)
            state["tokens"][id(bot)] = str(args[0])
            return bot

        def command(_vm, *args):
            _arity("comando", args, 3)
            bot, name_value, handler = args
            async def callback(ctx):
                response = await call_mux_handler_async(handler)
                if response is not None:
                    await ctx.send(str(response))
            bot.command(name=str(name_value))(callback)
            return True

        def start(_vm, *args):
            _arity("iniciar_bot", args, 1)
            token = state["tokens"].get(id(args[0]))
            if not token:
                raise _error("Crea el bot con un token válido antes de iniciarlo")
            args[0].run(token)
            return True

        return {"crear_bot": _wrap("crear_bot", create_bot),
                "comando": _wrap("comando", command), "iniciar_bot": _wrap("iniciar_bot", start)}

    if name == "telegram_bot":
        state = {"tokens": {}}

        def create_bot(_vm, *args):
            _arity("crear_bot", args, 1)
            try:
                from telegram.ext import Application
            except ImportError as exc:
                raise _error("telegram_bot requiere instalar mux-lang[telegram]") from exc
            bot = {"application_builder": Application, "commands": []}
            state["tokens"][id(bot)] = str(args[0])
            return bot

        def command(_vm, *args):
            _arity("comando", args, 3)
            bot, command_name, handler = args
            bot["commands"].append((str(command_name), handler))
            return True

        def start(_vm, *args):
            _arity("iniciar_bot", args, 1)
            bot = args[0]
            token = state["tokens"].get(id(bot))
            if not token:
                raise _error("Crea el bot con un token válido antes de iniciarlo")
            application = bot["application_builder"].builder().token(token).build()
            for command_name, handler in bot["commands"]:
                async def callback(update, context, mux_handler=handler):
                    response = await call_mux_handler_async(mux_handler)
                    if response is not None and update.message is not None:
                        await update.message.reply_text(str(response))
                from telegram.ext import CommandHandler
                application.add_handler(CommandHandler(command_name, callback))
            application.run_polling()
            return True

        return {"crear_bot": _wrap("crear_bot", create_bot),
                "comando": _wrap("comando", command), "iniciar_bot": _wrap("iniciar_bot", start)}

    if name == "whatsapp":
        def send_message(_vm, *args):
            _arity("send", args, 2)
            try:
                from twilio.rest import Client
            except ImportError as exc:
                raise _error("whatsapp requiere instalar mux-lang[whatsapp]") from exc
            account_sid = os.environ.get("MUX_TWILIO_ACCOUNT_SID")
            auth_token = os.environ.get("MUX_TWILIO_AUTH_TOKEN")
            sender = os.environ.get("MUX_TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
            if not account_sid or not auth_token:
                raise _error("Configura MUX_TWILIO_ACCOUNT_SID y MUX_TWILIO_AUTH_TOKEN")
            try:
                message = Client(account_sid, auth_token).messages.create(
                    from_=sender, to=str(args[0]), body=str(args[1]))
                return {"sid": message.sid, "status": message.status}
            except Exception as exc:
                raise _error(f"No se pudo enviar el mensaje de WhatsApp: {exc}") from exc

        return {"send": _wrap("send", send_message)}

    raise _error(f"Módulo estándar '{name}' no encontrado")


def _bounded_count(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 1_000_000:
        raise _error("El número de repeticiones debe ser un entero entre 0 y 1000000")
    return value


def _bounded_width(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 1_000_000:
        raise _error("La longitud debe ser un entero entre 0 y 1000000")
    return value


def _from_codepoints(values):
    if not isinstance(values, list):
        raise _error("from_ascii requiere una lista de códigos")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        raise _error("from_ascii requiere enteros Unicode")
    try:
        return "".join(chr(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise _error(f"Código Unicode no válido: {exc}") from exc
