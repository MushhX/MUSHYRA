"""Native standard-library modules exposed to Mux programs.

Optional integrations are imported lazily. Every exported function is wrapped
so the interpreter can provide its IO streams, script-relative paths and error
locations consistently.
"""

import base64
import binascii
import hashlib
import json
import math
import os
import random
import re
import smtplib
import sqlite3
import ssl
import time
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MAX_HTTP_RESPONSE_BYTES = 10 * 1024 * 1024


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
        def request(method, url, data=None, headers=None, timeout=10):
            parsed = urlparse(str(url))
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise _error("HTTP solo admite URL http(s) absolutas")
            body = None
            request_headers = dict(headers or {})
            if data is not None:
                if isinstance(data, (dict, list)):
                    body = json.dumps(data).encode("utf-8")
                    request_headers.setdefault("Content-Type", "application/json")
                else:
                    body = str(data).encode("utf-8")
            req = Request(str(url), data=body, headers=request_headers, method=method)
            try:
                with urlopen(req, timeout=float(timeout)) as response:
                    raw = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
                    if len(raw) > MAX_HTTP_RESPONSE_BYTES:
                        raise _error("La respuesta HTTP supera el límite de 10 MiB")
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
            _arity("get", args, 1, 3)
            return request("GET", args[0], headers=args[1] if len(args) > 1 else None,
                           timeout=args[2] if len(args) > 2 else 10)

        def post(_vm, *args):
            _arity("post", args, 2, 4)
            return request("POST", args[0], args[1],
                           args[2] if len(args) > 2 else None,
                           args[3] if len(args) > 3 else 10)

        return {"get": _wrap("get", get), "post": _wrap("post", post)}

    if name == "filesystem":
        def path_for(vm, value):
            path = Path(str(value)).expanduser()
            return path if path.is_absolute() else Path(vm.current_dir) / path

        def read(vm, *args):
            _arity("read", args, 1, 2)
            try:
                return path_for(vm, args[0]).read_text(encoding=args[1] if len(args) > 1 else "utf-8")
            except OSError as exc:
                raise _error(f"No se pudo leer {args[0]!r}: {exc}") from exc

        def write(vm, *args):
            _arity("write", args, 2, 3)
            try:
                path = path_for(vm, args[0])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(args[1]), encoding=args[2] if len(args) > 2 else "utf-8")
                return True
            except OSError as exc:
                raise _error(f"No se pudo escribir {args[0]!r}: {exc}") from exc

        def append(vm, *args):
            _arity("append", args, 2, 3)
            try:
                path = path_for(vm, args[0])
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding=args[2] if len(args) > 2 else "utf-8") as stream:
                    stream.write(str(args[1]))
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
                return sorted(child.name for child in path_for(vm, args[0]).iterdir())
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
                return json.loads(args[0])
            except (TypeError, json.JSONDecodeError) as exc:
                raise _error(f"JSON no válido: {exc}") from exc

        def stringify(_vm, *args):
            _arity("stringify", args, 1)
            try:
                return json.dumps(args[0], ensure_ascii=False, separators=(",", ":"))
            except (TypeError, ValueError) as exc:
                raise _error(f"No se puede serializar JSON: {exc}") from exc

        def pretty(_vm, *args):
            _arity("pretty", args, 1)
            try:
                return json.dumps(args[0], ensure_ascii=False, indent=2)
            except (TypeError, ValueError) as exc:
                raise _error(f"No se puede serializar JSON: {exc}") from exc

        def load(vm, *args):
            _arity("load", args, 1)
            from .native_stdlib import create_module
            fs = create_module("filesystem", vm)["read"]
            return parse(vm, fs(vm, args[0]))

        def save(vm, *args):
            _arity("save", args, 2)
            from .native_stdlib import create_module
            fs = create_module("filesystem", vm)["write"]
            fs(vm, args[0], pretty(vm, args[1]))
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
                "encrypt": _wrap("encrypt", cipher_encrypt),
                "decrypt": _wrap("decrypt", cipher_decrypt)}

    if name == "regex":
        def compile_pattern(pattern):
            try:
                return re.compile(str(pattern))
            except re.error as exc:
                raise _error(f"Expresión regular no válida: {exc}") from exc

        def match(_vm, *args):
            _arity("match", args, 2)
            return compile_pattern(args[0]).search(str(args[1])) is not None

        def find_all(_vm, *args):
            _arity("find_all", args, 2)
            return compile_pattern(args[0]).findall(str(args[1]))

        def replace(_vm, *args):
            _arity("replace", args, 3)
            return compile_pattern(args[0]).sub(str(args[1]), str(args[2]))

        def split(_vm, *args):
            _arity("split", args, 2)
            return compile_pattern(args[0]).split(str(args[1]))

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
            "extract_numbers": lambda _vm, text: re.findall(r"\d+", str(text)),
            "extract_emails": lambda _vm, text: re.findall(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(text)),
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
            if not math.isfinite(seconds) or seconds < 0:
                raise _error("sleep requiere segundos finitos y no negativos")
            time.sleep(seconds)
            return True

        def now(_vm, *args):
            _arity("now", args, 0)
            return int(time.time())

        def format_date(_vm, *args):
            _arity("format_date", args, 1, 2)
            try:
                return datetime.fromtimestamp(float(args[0])).strftime(args[1] if len(args) > 1 else "%Y-%m-%d %H:%M:%S")
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
                "sleep": _wrap("sleep", sleep), "format_date": _wrap("format_date", format_date),
                "get_year": current_part("year"), "get_month": current_part("month"),
                "get_day": current_part("day"), "get_hour": current_part("hour"),
                "get_minute": current_part("minute"), "get_second": current_part("second"),
                "measure_time": _wrap("measure_time", measure_time)}

    if name == "database":
        state = {"connection": None}

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
            return f" WHERE {identifier(field)} {operator} ?", [value]

        def connect(vm, *args):
            _arity("connect", args, 1)
            path = Path(str(args[0])).expanduser()
            if not path.is_absolute():
                path = Path(vm.current_dir) / path
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                previous = state["connection"]
                state["connection"] = None
                if previous is not None:
                    previous.close()
                state["connection"] = sqlite3.connect(str(path))
                state["connection"].row_factory = sqlite3.Row
                return state["connection"]
            except sqlite3.Error as exc:
                raise _error(f"No se pudo abrir la base de datos: {exc}") from exc

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
                connection().commit()
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
                connection().commit()
                return cursor.lastrowid
            except sqlite3.Error as exc:
                raise _error(f"No se pudo insertar: {exc}") from exc

        def select(_vm, *args):
            _arity("select", args, 1, 2)
            clause, params = where_clause(args[1] if len(args) > 1 else None)
            try:
                rows = connection().execute(f"SELECT * FROM {identifier(args[0])}{clause}", params)
                return [dict(row) for row in rows.fetchall()]
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
                connection().commit()
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
                connection().commit()
                return cursor.rowcount
            except sqlite3.Error as exc:
                raise _error(f"No se pudo eliminar: {exc}") from exc

        def execute(_vm, *args):
            _arity("execute", args, 1, 2)
            params = args[1] if len(args) > 1 else []
            if not isinstance(params, list):
                raise _error("execute espera los parámetros como lista")
            try:
                cursor = connection().execute(str(args[0]), params)
                connection().commit()
                if cursor.description:
                    return [dict(row) for row in cursor.fetchall()]
                return cursor.rowcount
            except sqlite3.Error as exc:
                raise _error(f"Consulta SQL no válida: {exc}") from exc

        def close(_vm, *args):
            _arity("close", args, 0, 1)
            conn = args[0] if args else state["connection"]
            if conn is not None:
                conn.close()
            state["connection"] = None
            return True

        return {key: _wrap(key, fn) for key, fn in {
            "connect": connect, "create_table": create_table, "insert": insert,
            "select": select, "update": update, "delete": delete,
            "execute": execute, "close": close,
        }.items()}

    if name == "email":
        config = {"host": None, "port": None, "username": None, "password": None}

        def configure(_vm, *args):
            _arity("configure_smtp", args, 4)
            config.update(host=str(args[0]), port=int(args[1]), username=str(args[2]), password=str(args[3]))
            return True

        def send_mail(recipient, subject, body, html=None, attachment=None):
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
                path = Path(str(attachment)).expanduser()
                if not path.is_absolute():
                    path = Path(interpreter.current_dir) / path
                try:
                    payload = path.read_bytes()
                except OSError as exc:
                    raise _error(f"No se pudo leer el adjunto: {exc}") from exc
                message.add_attachment(payload, maintype="application", subtype="octet-stream", filename=path.name)
            try:
                if config["port"] == 465:
                    smtp = smtplib.SMTP_SSL(config["host"], config["port"], timeout=15, context=ssl.create_default_context())
                else:
                    smtp = smtplib.SMTP(config["host"], config["port"], timeout=15)
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
            return send_mail(*args)

        def send_html(_vm, *args):
            _arity("send_html", args, 3)
            return send_mail(args[0], args[1], "Mensaje en formato HTML", html=args[2])

        def send_attachment(_vm, *args):
            _arity("send_with_attachment", args, 4)
            return send_mail(args[0], args[1], args[2], attachment=args[3])

        return {key: _wrap(key, fn) for key, fn in {
            "configure_smtp": configure, "send": send,
            "send_html": send_html, "send_with_attachment": send_attachment,
        }.items()}

    if name == "console":
        colors = {"black": 30, "red": 31, "green": 32, "yellow": 33,
                  "blue": 34, "magenta": 35, "cyan": 36, "white": 37}

        def styled(text, code):
            value = str(text)
            return f"\033[{code}m{value}\033[0m" if getattr(interpreter.output, "isatty", lambda: False)() else value

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
            for index, item in enumerate(args[0], 1):
                print(f"{index}. {item}", file=interpreter.output)
            answer = interpreter.input("Selecciona una opción: ")
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
                answer = interpreter.input(f"{args[0]} (s/n): ").strip().lower()
            except EOFError as exc:
                raise _error("No hay más entrada disponible") from exc
            return answer in ("s", "si", "sí", "y", "yes")

        def table(_vm, *args):
            _arity("table", args, 1)
            rows = args[0]
            if not isinstance(rows, list) or not rows:
                print("(sin filas)", file=interpreter.output)
                return True
            if not all(isinstance(row, dict) for row in rows):
                raise _error("table requiere una lista de diccionarios")
            columns = list(dict.fromkeys(key for row in rows for key in row))
            widths = {key: max(len(str(key)), *(len(str(row.get(key, ""))) for row in rows)) for key in columns}
            print(" | ".join(str(key).ljust(widths[key]) for key in columns), file=interpreter.output)
            print("-+-".join("-" * widths[key] for key in columns), file=interpreter.output)
            for row in rows:
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
            if not 0 < int(args[1]) < 65536:
                raise _error("El puerto debe estar entre 1 y 65535")
            args[0].run(host="127.0.0.1", port=int(args[1]))
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
                response = interpreter.call_value(handler, [])
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
                    response = interpreter.call_value(mux_handler, [])
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
