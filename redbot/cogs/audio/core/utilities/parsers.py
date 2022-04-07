import re
import struct

from typing import Final, Optional

import aiohttp
from red_commons.logging import getLogger

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ...audio_dataclasses import Query

log = getLogger("red.cogs.Audio.cog.Utilities.Parsing")

STREAM_TITLE: Final[re.Pattern] = re.compile(rb"StreamTitle='([^']*)';")


class ParsingUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def icyparser(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url, headers={"Icy-MetaData": "1"}) as resp:
                metaint = int(resp.headers["icy-metaint"])
                for _ in range(5):
                    await resp.content.readexactly(metaint)
                    metadata_length = struct.unpack("B", await resp.content.readexactly(1))[0] * 16
                    metadata = await resp.content.readexactly(metadata_length)
                    m = re.search(STREAM_TITLE, metadata.rstrip(b"\0"))
                    if m:
                        title = m.group(1)
                        if title:
                            title = title.decode("utf-8", errors="replace")
                            return title
                    else:
                        return None
        except (KeyError, aiohttp.ClientConnectionError, aiohttp.ClientResponseError):
            return None

    async def scrape_bandcamp_url(self, query: str) -> "Query":
        # Try and webscrape for the original bandcamp url inside the custom domain's html body
        try:
            async with self.session.get(query) as response:
                html = await response.text()
                # Get the index of 'og:url"'
                ind = html.index('og:url"')
                # If found
                if ind > -1:
                    # Get the index of the closing tag
                    end_ind = html.index(">", ind)
                    if end_ind > -1:
                        # Split '<meta property="og:url"' and 'content="<bandcamp url>">' using 're' library
                        # and get the content side
                        content = re.split(" +", html[ind:end_ind])[1]
                        # Refine to get only the new bandcamp url
                        bandcamp_url = content[content.index('"') + 1 : -1]
                        # Recreate the query with the new url
                        return Query.process_input(bandcamp_url, self.local_folder_current_path)
        except Exception as e:
            return None
        return None
