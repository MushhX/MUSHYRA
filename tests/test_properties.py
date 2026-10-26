from hypothesis import given, settings, strategies as st

from mux_lang.lexer import Lexer, MuxError
from mux_lang.parser import Parser


@settings(max_examples=200, deadline=None)
@given(st.text(max_size=120))
def test_lexer_and_parser_never_leak_common_input_errors(source):
    try:
        tokens = Lexer(source).tokenize()
        Parser(tokens).parse()
    except MuxError:
        pass
