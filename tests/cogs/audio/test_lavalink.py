from redbot.cogs.audio.core.events import lavalink as lavalink_events


def test_track_error_within_embed_limit_is_unchanged() -> None:
    error = "x" * lavalink_events._EMBED_DESCRIPTION_LIMIT

    assert lavalink_events._truncate_track_error(error) == error


def test_oversized_track_error_is_clearly_truncated(monkeypatch) -> None:
    monkeypatch.setattr(lavalink_events, "_", lambda message: message)
    notice = "\n\n[Error truncated due to length.]"
    error = "x" * lavalink_events._EMBED_DESCRIPTION_LIMIT + "tail"

    truncated_error = lavalink_events._truncate_track_error(error)

    assert len(truncated_error) == lavalink_events._EMBED_DESCRIPTION_LIMIT
    assert truncated_error.endswith(notice)
    assert (
        truncated_error == error[: lavalink_events._EMBED_DESCRIPTION_LIMIT - len(notice)] + notice
    )
    assert "tail" not in truncated_error
