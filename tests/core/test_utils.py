import textwrap
from redbot.core.utils import chat_formatting


def test_bordered_symmetrical():
    expected = textwrap.dedent(
        """\
    ┌──────────────┐    ┌─────────────┐
    │one           │    │four         │
    │two           │    │five         │
    │three         │    │six          │
    └──────────────┘    └─────────────┘"""
    )
    col1, col2 = ["one", "two", "three"], ["four", "five", "six"]
    assert chat_formatting.bordered(col1, col2) == expected


def test_bordered_asymmetrical():
    expected = textwrap.dedent(
        """\
    ┌──────────────┐    ┌──────────────┐
    │one           │    │four          │
    │two           │    │five          │
    │three         │    │six           │
    └──────────────┘    │seven         │
                        └──────────────┘"""
    )
    col1, col2 = ["one", "two", "three"], ["four", "five", "six", "seven"]
    assert chat_formatting.bordered(col1, col2) == expected


def test_bordered_asymmetrical_2():
    expected = textwrap.dedent(
        """\
    ┌──────────────┐    ┌─────────────┐
    │one           │    │five         │
    │two           │    │six          │
    │three         │    └─────────────┘
    │four          │                   
    └──────────────┘                   """
    )
    col1, col2 = ["one", "two", "three", "four"], ["five", "six"]
    assert chat_formatting.bordered(col1, col2) == expected


def test_bordered_ascii():
    expected = textwrap.dedent(
        """\
    ----------------    ---------------
    |one           |    |four         |
    |two           |    |five         |
    |three         |    |six          |
    ----------------    ---------------"""
    )
    col1, col2 = ["one", "two", "three"], ["four", "five", "six"]
    assert chat_formatting.bordered(col1, col2, ascii_border=True) == expected
