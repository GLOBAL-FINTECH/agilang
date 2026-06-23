from pathlib import Path

from agilang.checker import check_source
from agilang.formatter import format_source
from agilang.translator import AGILTranslator


def test_translates_typed_function_and_let():
    source = """
fn add(a: i32, b: i32) -> i32:
    let total: i32 = a + b
    return total
"""
    py = AGILTranslator().translate(source)
    assert "def add(a: int, b: int) -> int:" in py
    assert "total: int = a + b" in py


def test_struct_and_enum_translation():
    source = """
struct User:
    name: str
    age: i32

enum Status:
    PENDING
    ACTIVE
"""
    py = AGILTranslator().translate(source)
    assert "@dataclass" in py
    assert "class User:" in py
    assert "class Status(Enum):" in py
    assert "PENDING = auto()" in py


def test_checker_accepts_valid_program():
    report = check_source("""
fn main() -> i32:
    let x: i32 = 1
    print(x)
    return 0
""")
    assert report.ok


def test_formatter_normalizes_let_spacing():
    assert "let x: i32 = 1" in format_source("let x : i32=1\n")

from agilang.lexer import tokenize


def test_lexer_emits_positions():
    tokens = tokenize('fn main() -> i32:\n    return 0\n')
    assert tokens[0].kind == "KEYWORD"
    assert tokens[0].value == "fn"
    assert tokens[0].line == 1
    assert any(t.value == "->" for t in tokens)


def test_type_alias_and_pub_fn_translation():
    source = """
type Money = f64
pub fn fee(amount: Money) -> Money:
    return amount * 0.025
"""
    py = AGILTranslator().translate(source)
    assert "Money = float  # type alias" in py
    assert "def fee(amount: Money) -> Money:" in py
    assert "# exported" in py


def test_checker_rejects_const_reassignment():
    report = check_source("""
fn main() -> i32:
    const rate: f64 = 0.025
    rate = 0.03
    return 0
""")
    assert not report.ok
    assert "E401" in report.format()

from agilang.parser import parse_source
from agilang.typechecker import typecheck_source
from agilang.c_backend import to_c_source


def test_parser_builds_function_ast():
    program = parse_source('fn main() -> i32:\n    let x: i32 = 7\n    return x\n')
    assert program.body[0].name == 'main'
    assert program.body[0].body[0].name == 'x'


def test_typechecker_rejects_string_to_i32():
    report = typecheck_source('fn main() -> i32:\n    let x: i32 = "bad"\n    return 0\n')
    assert not report.ok
    assert 'ETYPE31' in report.format()


def test_c_backend_generates_print_and_function():
    result = to_c_source('fn add(a: i32, b: i32) -> i32:\n    return a + b\n\nfn main() -> i32:\n    let x: i32 = add(2, 3)\n    print("x", x)\n    return 0\n')
    assert result.ok, result.format()
    assert 'int add(int a, int b)' in result.c_source
    assert 'printf("x %d\\n", x);' in result.c_source
