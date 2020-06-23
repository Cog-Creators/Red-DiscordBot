from __future__ import annotations

import logging
import sys
import traceback

import wavelink

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.apis.audio._internal.wavelink.events import QueueEnd
from redbot.core.apis.audio._internal.wavelink import RedNode

log = logging.getLogger("red.core.apis.audio.nodes")

__all__ = ["AudioAPIEvents"]


class AudioAPIEvents(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot: Red):
        self.bot = bot

    @wavelink.WavelinkMixin.listener()
    async def on_wavelink_error(self, listener, error: Exception):
        """Event dispatched when an error is raised during mixin listener dispatch.

        Parameters
        ------------
        listener:
            The listener where an exception was raised.
        error: Exception
            The exception raised when dispatching a mixin listener.
        """
        log.warning(f"Ignoring exception in listener {listener}")
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: RedNode):
        """Listener dispatched when a :class:`wavelink.node.Node` is connected and ready.

        Parameters
        ------------
        node: Node
            The node associated with the listener event.
        """

    @wavelink.WavelinkMixin.listener()
    async def on_track_start(self, node: RedNode, payload: wavelink.TrackStart):
        """Listener dispatched when a track starts.

        Parameters
        ------------
        node: Node
            The node associated with the listener event.
        payload: TrackStart
            The :class:`wavelink.events.TrackStart` payload.
        """

    @wavelink.WavelinkMixin.listener()
    async def on_track_end(self, node: RedNode, payload: wavelink.TrackEnd):
        """Listener dispatched when a track ends.

        Parameters
        ------------
        node: Node
            The node associated with the listener event.
        payload: TrackEnd
            The :class:`wavelink.events.TrackEnd` payload.
        """
        await payload.player.do_next()

    @wavelink.WavelinkMixin.listener()
    async def on_track_stuck(self, node: RedNode, payload: wavelink.TrackStuck):
        """Listener dispatched when a track is stuck.

        Parameters
        ------------
        node: Node
            The node associated with the listener event.
        payload: TrackStuck
            The :class:`wavelink.events.TrackStuck` payload.
        """
        await payload.player.do_next()

    @wavelink.WavelinkMixin.listener()
    async def on_track_exception(self, node: RedNode, payload: wavelink.TrackException):
        """Listener dispatched when a track errors.

        Parameters
        ------------
        node: Node
            The node associated with the listener event.
        payload: TrackException
            The :class:`wavelink.events.TrackException` payload.
        """
        await payload.player.do_next()

    @wavelink.WavelinkMixin.listener()
    async def on_websocket_closed(self, node: RedNode, payload: wavelink.WebsocketClosed):
        """Listener dispatched when a node websocket is closed by lavalink.

        Parameters
        ------------
        node: Node
            The node associated with the listener event.
        payload: WebsocketClosed
            The :class:`wavelink.events.WebsocketClosed` payload.
        """

    @wavelink.WavelinkMixin.listener()
    async def on_queue_end(self, node: RedNode, payload: QueueEnd):
        """Listener dispatched when a player queue ends.

        Parameters
        ------------
        node: Node
            The node associated with the listener event.
        payload: QueueEnd
            The :class:`QueueEnd` payload.
        """
