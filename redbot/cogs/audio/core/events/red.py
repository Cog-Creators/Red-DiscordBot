import logging
from typing import Mapping

from redbot.core import commands
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Events.red")


class RedEvents(MixinMeta, metaclass=CompositeMetaClass):
    @commands.Cog.listener()
    async def on_red_api_tokens_update(
        self, service_name: str, api_tokens: Mapping[str, str]
    ) -> None:
        if service_name == "youtube":
            self.api_interface.youtube_api.update_token(api_tokens)
        elif service_name == "spotify":
            self.api_interface.spotify_api.update_token(api_tokens)
        elif service_name == "audiodb":
            self.api_interface.global_cache_api.update_token(api_tokens)
