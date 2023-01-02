import textwrap

import pytest

from redbot.core.dev_commands import cleanup_code


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
