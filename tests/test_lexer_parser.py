from mushyra.ast_nodes import ASTNode
from mushyra.lexer import Lexer, MushyraError
from mushyra.parser import Parser


def test_token_keeps_legacy_tuple_shape_and_offsets():
    token = Lexer("let valor = 1_000\r\n").tokenize()[0]
    assert tuple(token) == ("LET", "let", 1)
    assert token.column == 1
    assert token.offset == 0
    assert token.end_offset == 3


def test_numeric_separators_and_exponents_parse():
    tree = Parser(Lexer("let n = 1_024.5e2\n").tokenize()).parse()
    assert isinstance(tree[0], ASTNode)
    assert tree[0][2][1] == 102450.0
    assert tree[0].span.start_line == 1
    assert tree[0].span.end_column > tree[0].span.start_column


def test_invalid_numeric_literal_has_source_location():
    try:
        Lexer("let n = 1e\n", "numeric.myr").tokenize()
    except MushyraError as error:
        assert error.path == "numeric.myr"
        assert error.line == 1
        assert "numérico" in error.message
    else:
        raise AssertionError("se esperaba MushyraError")


def test_parser_marks_eof_as_incomplete_for_repl():
    try:
        Parser(Lexer("if true\nprint(1)\n").tokenize()).parse()
    except MushyraError as error:
        assert error.incomplete is True
    else:
        raise AssertionError("se esperaba una declaración end")


def test_formatted_ast_nodes_are_tuple_compatible():
    tree = Parser(Lexer("let x = 2\n").tokenize()).parse()
    assert tree[0] == ("let", "x", ("number", 2))
    assert isinstance(tree[0], ASTNode)


def test_parser_keeps_source_map_reference_stable():
    parser = Parser(Lexer("print(1)\n").tokenize(), "stable.myr")
    source_map = parser.source_map
    tree = parser.parse()
    assert parser.source_map is source_map
    assert id(tree[0]) in source_map
