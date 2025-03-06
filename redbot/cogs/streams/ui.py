from typing import List
import discord

from redbot.core.bot import Red
from redbot.core.i18n import Translator


_ = Translator("Streams", __file__)

class TwitchGameSelector(discord.ui.Select):
    def __init__(self, games: List[discord.ui.SelectOption]):
        super.__init__(placeholder="Please choose a game...", min_values=1, max_values=1, options=games)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(_("Adding {game} to the list of games to alert for...").format(game=self.values[0]))
        self.view.stop()

class TwitchGameSelectorView(discord.ui.View):
    def __init__(self, selector: TwitchGameSelector, timeout: int = 60):
        self.timeout = timeout
        super().__init__()
        self.add_item(selector)
