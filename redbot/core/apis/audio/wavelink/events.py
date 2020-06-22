from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from .overwrites import RedPlayer, RedTrack


class QueueEnd:
    """Event dispatched on QueueEnd.

    Attributes
    ------------
    player: :class:`RedPlayer`
        The player associated with the event.
    track: :class:`RedTrack`
        The track associated with the event.
    """

    __slots__ = ("track", "player")

    def __init__(self, data: dict):
        self.track = data.get("track")
        self.player = data.get("player")

    def __str__(self):
        return "QueueEnd"
