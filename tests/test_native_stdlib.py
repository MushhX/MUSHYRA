import io

import pytest

from mux_lang.interpreter import Interpreter
from mux_lang.lexer import Lexer, MuxError
from mux_lang.native_stdlib import create_module
from mux_lang.parser import Parser


def run_file(source, filename):
    parser = Parser(Lexer(source, str(filename)).tokenize(), str(filename))
    vm = Interpreter(output=io.StringIO(), source_map=parser.source_map)
    vm.run(parser.parse(), str(filename))
    return vm


def test_json_rejects_duplicate_keys_and_nonstandard_constants():
    vm = Interpreter()
    module = create_module("json", vm)
    with pytest.raises(MuxError, match="duplicada"):
        vm.call_value(module["parse"], ['{"x":1,"x":2}'])
    with pytest.raises(MuxError, match="no estándar"):
        vm.call_value(module["parse"], ["NaN"])


def test_filesystem_atomic_write_obeys_sandbox(tmp_path):
    vm = Interpreter(allowed_root=tmp_path)
    vm.current_dir = str(tmp_path)
    module = create_module("filesystem", vm)
    assert vm.call_value(module["write"], ["data/result.txt", "ok"])
    assert (tmp_path / "data" / "result.txt").read_text(encoding="utf-8") == "ok"
    with pytest.raises(MuxError, match="fuera del directorio permitido"):
        vm.call_value(module["write"], ["../escape.txt", "no"])


def test_sqlite_pagination_and_transactions(tmp_path):
    vm = run_file('''import database as db
let connection = db.connect("records.sqlite")
db.create_table("records", ["id", "name"])
db.begin()
db.insert("records", {"name": "one"})
db.rollback()
print(len(db.select("records")))
db.insert("records", {"name": "two"})
print(db.select("records", null, 1, 0)[0]["name"])
db.close(connection)
''', tmp_path / "program.mux")
    assert vm.output.getvalue() == "0\ntwo\n"


def test_crypto_password_hash_and_token_are_secure_apis():
    vm = Interpreter()
    crypto = create_module("crypto", vm)
    encoded = vm.call_value(crypto["password_hash"], ["correct horse"])
    assert encoded.startswith("scrypt$1$")
    assert vm.call_value(crypto["password_verify"], ["correct horse", encoded]) is True
    assert vm.call_value(crypto["password_verify"], ["wrong", encoded]) is False
    token = vm.call_value(crypto["generate_token"], [])
    assert len(token) >= 32


def test_http_blocks_loopback_by_default():
    vm = Interpreter()
    http = create_module("http", vm)
    with pytest.raises(MuxError, match="dirección privada"):
        vm.call_value(http["get"], ["http://127.0.0.1/"])


def test_sqlite_sandbox_blocks_external_database_attachment(tmp_path):
    vm = Interpreter(allowed_root=tmp_path)
    vm.current_dir = str(tmp_path)
    database = create_module("database", vm)
    vm.call_value(database["connect"], ["inside.sqlite"])
    with pytest.raises(MuxError, match="fuera de sandbox_root"):
        vm.call_value(database["execute"], ["ATTACH DATABASE 'outside.sqlite' AS external"])


def test_regex_outputs_are_bounded():
    vm = Interpreter()
    regex = create_module("regex", vm)
    with pytest.raises(MuxError, match="10 Mi caracteres"):
        vm.call_value(regex["replace"], [".", "x" * (10 * 1024 * 1024 + 1), "a"])
