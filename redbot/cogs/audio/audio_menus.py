from typing import List, Tuple, Dict, Any, Optional

import discord

from redbot.core.i18n import Translator
from redbot.core.utils import chat_formatting as chatutils
from redbot.core.utils.menus import PagedOptionsMenu

_ = Translator("Audio", __file__)


class PlayListPickerMenu(PagedOptionsMenu, exit_button=True, initial_emojis=("⬅", "❌", "➡")):
    def __init__(self, *, accounts: List[Tuple[int, Dict[str, Any]]], **kwargs) -> None:
        self._accounts = accounts
        self._cur_rank = 0
        super().__init__(pages=[], arrows_always=True, **kwargs)

