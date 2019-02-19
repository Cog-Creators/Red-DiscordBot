from pathlib import Path
import logging

from .audio import Audio
from .manager import start_lavalink_server, maybe_download_lavalink
from redbot.core import commands
from redbot.core.data_manager import cog_data_path
import redbot.core

log = logging.getLogger("red.audio")

LAVALINK_DOWNLOAD_URL = (
    "https://github.com/Cog-Creators/Red-DiscordBot/releases/download/{}/Lavalink.jar"
).format(redbot.core.__version__)

LAVALINK_DOWNLOAD_DIR = cog_data_path(raw_name="Audio")
LAVALINK_JAR_FILE = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"

APP_YML_FILE = LAVALINK_DOWNLOAD_DIR / "application.yml"
BUNDLED_APP_YML_FILE = Path(__file__).parent / "data/application.yml"


async def setup(bot: commands.Bot):
    cog = Audio(bot)
    if not await cog.config.use_external_lavalink():
        await maybe_download_lavalink(bot.loop, cog)
        await start_lavalink_server(bot.loop)

    await cog.initialize()

    bot.add_cog(cog)
