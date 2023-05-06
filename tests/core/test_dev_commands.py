import sys
import textwrap
from unittest.mock import MagicMock

import pytest

from redbot.core import commands
from redbot.core.dev_commands import DevOutput, cleanup_code


# the examples are based on how the markdown ends up being rendered by Discord
@pytest.mark.parametrize(
    "content,source",
    (
        # no markdown to strip
        (
            "x = 1",
            "x = 1",
        ),
        # inline with single backticks
        (
            "`x = 1`",
            "x = 1",
        ),
        # inline with double backticks
        (
            "``x = 1``",
            "x = 1",
        ),
        # code block within a single line
        (
            "```x = 1```",
            "x = 1",
        ),
        # code block with code in first line and closing backquotes in separate line
        (
            """\
            ```x = 1
            ```""",
            "x = 1",
        ),
        # code block with closing backquotes in same line
        (
            """\
            ```
            x = 1```""",
            "x = 1",
        ),
        # code block with opening and closing backquotes in separate lines
        (
            """\
            ```
            x = 1
            ```""",
            "x = 1",
        ),
        # code block with language specified and closing backquotes in separate line
        (
            """\
            ```py
            x = 1
            ```""",
            "x = 1",
        ),
        (
            """\
            ```python
            x = 1
            ```""",
            "x = 1",
        ),
        # code block with language specified and closing backquotes in same line
        (
            """\
            ```py
            x = 1```""",
            "x = 1",
        ),
        (
            """\
            ```python
            x = 1```""",
            "x = 1",
        ),
        # code block with the only line of code being a potentially valid language name
        # ('pass' is just a combination of letters) and being right after opening backquotes.
        (
            """\
            ```pass
            ```""",
            "pass",
        ),
        # leading newline characters should get stripped, ending backquotes on separate line
        (
            """\
            ```


            x = 1
            ```""",
            "x = 1",
        ),
        (
            """\
            ```python


            x = 1
            ```""",
            "x = 1",
        ),
        # leading newline characters should get stripped, ending backquotes on same line
        (
            """\
            ```


            x = 1```""",
            "x = 1",
        ),
        (
            """\
            ```python


            x = 1```""",
            "x = 1",
        ),
    ),
)
def test_cleanup_code(content: str, source: str) -> None:
    content = textwrap.dedent(content)
    source = textwrap.dedent(source)
    assert cleanup_code(content) == source


def _get_dev_output(source: str) -> DevOutput:
    return DevOutput(
        MagicMock(spec=commands.Context),
        source=source,
        filename="<test run>",
        env={"__builtins__": __builtins__, "__name__": "__main__", "_": None},
    )


async def _run_dev_output(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    result: str,
    *,
    debug: bool = False,
    eval: bool = False,
    repl: bool = False,
) -> None:
    source = textwrap.dedent(source)
    result = textwrap.dedent(result)
    monkeypatch.setattr("redbot.core.dev_commands.sanitize_output", lambda ctx, s: s)

    if debug:
        output = _get_dev_output(source)
        await output.run_debug()
        assert str(output) == result
        # ensure that our Context mock is never actually used by anything
        assert not output.ctx.mock_calls

    if eval:
        output = _get_dev_output(source.replace("<module>", "func"))
        await output.run_eval()
        assert str(output) == result.replace("<module>", "func")
        # ensure that our Context mock is never actually used by anything
        assert not output.ctx.mock_calls

    if repl:
        output = _get_dev_output(source)
        await output.run_repl()
        assert str(output) == result
        # ensure that our Context mock is never actually used by anything
        assert not output.ctx.mock_calls


EXPRESSION_TESTS = {
    # invalid syntax
    "12x\n": (
        (
            lambda v: v < (3, 10),
            """\
              File "<test run>", line 1
                12x
                  ^
            SyntaxError: invalid syntax
            """,
        ),
        (
            lambda v: v >= (3, 10),
            """\
              File "<test run>", line 1
                12x
                 ^
            SyntaxError: invalid decimal literal
            """,
        ),
    ),
    "foo(x, z for z in range(10), t, w)": (
        (
            lambda v: v < (3, 10),
            """\
              File "<test run>", line 1
                foo(x, z for z in range(10), t, w)
                       ^
            SyntaxError: Generator expression must be parenthesized
            """,
        ),
        (
            lambda v: v >= (3, 10),
            """\
              File "<test run>", line 1
                foo(x, z for z in range(10), t, w)
                       ^^^^^^^^^^^^^^^^^^^^
            SyntaxError: Generator expression must be parenthesized
            """,
        ),
    ),
    # exception raised
    "abs(1 / 0)": (
        (
            lambda v: v < (3, 11),
            """\
            Traceback (most recent call last):
              File "<test run>", line 1, in <module>
                abs(1 / 0)
            ZeroDivisionError: division by zero
            """,
        ),
        (
            lambda v: v >= (3, 11),
            """\
            Traceback (most recent call last):
              File "<test run>", line 1, in <module>
                abs(1 / 0)
                    ~~^~~
            ZeroDivisionError: division by zero
            """,
        ),
    ),
}
STATEMENT_TESTS = {
    # invalid syntax
    """\
    def x():
        12x
    """: (
        (
            lambda v: v < (3, 10),
            """\
              File "<test run>", line 2
                12x
                  ^
            SyntaxError: invalid syntax
            """,
        ),
        (
            lambda v: v >= (3, 10),
            """\
              File "<test run>", line 2
                12x
                 ^
            SyntaxError: invalid decimal literal
            """,
        ),
    ),
    """\
    def x():
        foo(x, z for z in range(10), t, w)
    """: (
        (
            lambda v: v < (3, 10),
            """\
              File "<test run>", line 2
                foo(x, z for z in range(10), t, w)
                       ^
            SyntaxError: Generator expression must be parenthesized
            """,
        ),
        (
            lambda v: v >= (3, 10),
            """\
              File "<test run>", line 2
                foo(x, z for z in range(10), t, w)
                       ^^^^^^^^^^^^^^^^^^^^
            SyntaxError: Generator expression must be parenthesized
            """,
        ),
    ),
    # exception raised
    """\
    print(123)
    try:
        abs(1 / 0)
    except ValueError:
        pass
    """: (
        (
            lambda v: v < (3, 11),
            """\
            123
            Traceback (most recent call last):
              File "<test run>", line 3, in <module>
                abs(1 / 0)
            ZeroDivisionError: division by zero
            """,
        ),
        (
            lambda v: v >= (3, 11),
            """\
            123
            Traceback (most recent call last):
              File "<test run>", line 3, in <module>
                abs(1 / 0)
                    ~~^~~
            ZeroDivisionError: division by zero
            """,
        ),
    ),
}


@pytest.mark.parametrize(
    "source,result",
    [
        (source, result)
        for source, results in EXPRESSION_TESTS.items()
        for condition, result in results
        if condition(sys.version_info)
    ],
)
async def test_format_exception_expressions(
    monkeypatch: pytest.MonkeyPatch, source: str, result: str
) -> None:
    await _run_dev_output(monkeypatch, source, result, debug=True, repl=True)


@pytest.mark.parametrize(
    "source,result",
    [
        (source, result)
        for source, results in STATEMENT_TESTS.items()
        for condition, result in results
        if condition(sys.version_info)
    ],
)
async def test_format_exception_statements(
    monkeypatch: pytest.MonkeyPatch, source: str, result: str
) -> None:
    await _run_dev_output(monkeypatch, source, result, eval=True, repl=True)


async def test_successful_run_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    source = "print('hello world'), 123"
    result = "(None, 123)"
    await _run_dev_output(monkeypatch, source, result, debug=True)


async def test_successful_run_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    source = """\
    print("hello world")
    return 123
    """
    result = """\
    hello world
    123"""
    await _run_dev_output(monkeypatch, source, result, eval=True)


async def test_successful_run_repl_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    source = "print('hello world'), 123"
    result = """\
    hello world
    (None, 123)"""
    await _run_dev_output(monkeypatch, source, result, repl=True)


async def test_successful_run_repl_exec(monkeypatch: pytest.MonkeyPatch) -> None:
    source = """\
    print("hello")
    print("world")
    """
    result = """\
    hello
    world
    """
    await _run_dev_output(monkeypatch, source, result, repl=True)
