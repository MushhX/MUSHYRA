import io

import pytest

from mux_lang.interpreter import Interpreter
from mux_lang.lexer import Lexer, MuxError
from mux_lang.parser import Parser


def run_mux(source, filename="<stdin>", **options):
    parser = Parser(Lexer(source, filename).tokenize(), filename)
    tree = parser.parse()
    output = io.StringIO()
    vm = Interpreter(output=output, source_map=parser.source_map, **options)
    code = vm.run(tree, filename)
    return output.getvalue(), code


def test_closure_and_nonlocal_assignment():
    source = '''func outer()
    let count = 0
    func increment()
        nonlocal count
        count = count + 1
        return count
    end
    return increment
end
let next_value = outer()
print(next_value())
print(next_value())
'''
    output, _ = run_mux(source)
    assert output == "1\n2\n"


def test_boolean_operators_short_circuit():
    output, _ = run_mux('print(false && missing())\nprint(true || missing())\n')
    assert output == "False\nTrue\n"


def test_execution_budget_counts_expressions_and_stops_loops():
    with pytest.raises(MuxError, match="límite"):
        run_mux("loop\npass\nend\n", max_steps=12)


def test_call_depth_has_a_mux_error():
    source = "func recurse()\nreturn recurse()\nend\nrecurse()\n"
    with pytest.raises(MuxError, match="llamadas anidadas"):
        run_mux(source, max_call_depth=8)


def test_file_access_can_be_confined_to_a_root(tmp_path):
    vm = Interpreter(allowed_root=tmp_path)
    vm.current_dir = str(tmp_path)
    with pytest.raises(MuxError, match="fuera del directorio permitido"):
        vm.resolve_path("../outside.txt")


def test_run_preserves_exit_code():
    _output, code = run_mux("exit(7)\n")
    assert code == 7


def test_imported_function_errors_keep_their_source_file(tmp_path):
    (tmp_path / "library.mux").write_text("func fail()\n    missing()\nend\n", encoding="utf-8")
    main = tmp_path / "main.mux"
    main.write_text("import library as lib\nlib.fail()\n", encoding="utf-8")
    parser = Parser(Lexer(main.read_text(encoding="utf-8"), str(main)).tokenize(), str(main))
    vm = Interpreter(output=io.StringIO(), source_map=parser.source_map)
    with pytest.raises(MuxError) as captured:
        vm.run(parser.parse(), str(main))
    assert captured.value.path == str(tmp_path / "library.mux")
    assert captured.value.line == 2
