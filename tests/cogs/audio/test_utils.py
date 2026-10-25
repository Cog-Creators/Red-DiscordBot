from redbot.cogs.audio.utils import truncate

ELLIPSIS = "\N{HORIZONTAL ELLIPSIS}"


def test_truncate_leaves_short_text_untouched():
    assert truncate("hello", max_length=10) == "hello"


def test_truncate_keeps_text_at_the_limit():
    text = "x" * 10
    assert truncate(text, max_length=10) == text


def test_truncate_shortens_long_text_and_adds_placeholder():
    result = truncate("x" * 20, max_length=10)
    assert len(result) == 10
    assert result == "x" * 9 + ELLIPSIS


def test_truncate_uses_a_custom_placeholder():
    result = truncate("abcdefghij", max_length=6, placeholder="...")
    assert result == "abc..."
    assert len(result) == 6


def test_truncate_when_placeholder_does_not_fit():
    assert truncate("abcdef", max_length=2, placeholder="...") == ".."


def test_truncate_does_not_collapse_whitespace():
    text = "line one\n\n   line two"
    assert truncate(text, max_length=100) == text


def test_truncate_fits_a_long_error_in_a_discord_embed():
    # Discord rejects embed descriptions longer than 4096 characters.
    long_error = "Traceback line\n" * 1000
    result = truncate(long_error, max_length=4096)
    assert len(result) == 4096
    assert result.startswith("Traceback line")
    assert result.endswith(ELLIPSIS)
