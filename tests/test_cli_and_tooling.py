import json
from pathlib import Path

from mux_lang.cli import main
from mux_lang.formatter import format_source
from mux_lang.lexer import Lexer
from mux_lang.linter import lint_ast
from mux_lang.parser import Parser


def test_formatter_normalizes_block_indent():
    source = "func f()\nprint(1)\nend"
    assert format_source(source) == "func f()\n    print(1)\nend"


def test_formatter_keeps_delimited_expression_lines_aligned():
    source = "let values = [\n1,\n2\n]"
    assert format_source(source) == "let values = [\n    1,\n    2\n]"


def test_linter_reports_unreachable_code():
    tree = Parser(Lexer("func f()\nreturn\nprint(1)\nend\n").tokenize()).parse()
    assert any(item.code == "MUX101" for item in lint_ast(tree))


def test_cli_exposes_script_arguments(tmp_path, capsys):
    source = tmp_path / "args.mux"
    source.write_text("print(args[0])\n", encoding="utf-8")
    assert main([str(source), "--", "hello"]) == 0
    assert capsys.readouterr().out == "hello\n"


def test_cli_json_diagnostic_is_machine_readable(tmp_path, capsys):
    source = tmp_path / "invalid.mux"
    source.write_text("let x =\n", encoding="utf-8")
    assert main(["--diagnostics-format", "json", str(source)]) == 1
    diagnostic = json.loads(capsys.readouterr().err)
    assert diagnostic["message"]
    assert diagnostic["line"] == 1


def test_cli_check_does_not_execute_program(tmp_path, capsys):
    source = tmp_path / "check.mux"
    source.write_text("print(1)\n", encoding="utf-8")
    assert main(["--check", str(source)]) == 0
    assert capsys.readouterr().out == ""
