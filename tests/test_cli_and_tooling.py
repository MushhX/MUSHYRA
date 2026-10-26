import json
from pathlib import Path

from mushyra.cli import main
from mushyra.formatter import format_source
from mushyra.lexer import Lexer
from mushyra.linter import lint_ast
from mushyra.parser import Parser


def test_formatter_normalizes_block_indent():
    source = "func f()\nprint(1)\nend"
    assert format_source(source) == "func f()\n    print(1)\nend"


def test_formatter_keeps_delimited_expression_lines_aligned():
    source = "let values = [\n1,\n2\n]"
    assert format_source(source) == "let values = [\n    1,\n    2\n]"


def test_linter_reports_unreachable_code():
    tree = Parser(Lexer("func f()\nreturn\nprint(1)\nend\n").tokenize()).parse()
    assert any(item.code == "MYR101" for item in lint_ast(tree))


def test_cli_exposes_script_arguments(tmp_path, capsys):
    source = tmp_path / "args.myr"
    source.write_text("print(args[0])\n", encoding="utf-8")
    assert main([str(source), "--", "hello"]) == 0
    assert capsys.readouterr().out == "hello\n"


def test_cli_json_diagnostic_is_machine_readable(tmp_path, capsys):
    source = tmp_path / "invalid.myr"
    source.write_text("let x =\n", encoding="utf-8")
    assert main(["--diagnostics-format", "json", str(source)]) == 1
    diagnostic = json.loads(capsys.readouterr().err)
    assert diagnostic["message"]
    assert diagnostic["line"] == 1


def test_cli_check_does_not_execute_program(tmp_path, capsys):
    source = tmp_path / "check.myr"
    source.write_text("print(1)\n", encoding="utf-8")
    assert main(["--check", str(source)]) == 0
    assert capsys.readouterr().out == ""
