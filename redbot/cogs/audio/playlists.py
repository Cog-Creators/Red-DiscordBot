from collections import namedtuple
from enum import Enum, unique
from typing import List, Optional, Union

import discord
import lavalink

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list
from .errors import InvalidPlaylistScope, MissingAuthor, MissingGuild, NotAllowed

_config = None
_bot = None

__all__ = [
    "Playlist",
    "PlaylistScope",
    "get_playlist",
    "get_all_playlist",
    "create_playlist",
    "reset_playlist",
    "delete_playlist",
    "humanize_scope",
    "FakePlaylist",
]

FakePlaylist = namedtuple("Playlist", "author")


@unique
class PlaylistScope(Enum):
    GLOBAL = "GLOBALPLAYLIST"
    GUILD = "GUILDPLAYLIST"
    USER = "USERPLAYLIST"

    def __str__(self):
        return "{0}".format(self.value)

    @staticmethod
    def list():
        return list(map(lambda c: c.value, PlaylistScope))


def _pass_config_to_playlist(config: Config, bot: Red):
    global _config, _bot
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot


def standardize_scope(scope) -> str:
    scope = scope.upper()
    valid_scopes = ["GLOBAL", "GUILD", "AUTHOR", "USER", "SERVER", "MEMBER", "BOT"]

    if scope in PlaylistScope.list():
        return scope
    elif scope not in valid_scopes:
        raise InvalidPlaylistScope(
            f'"{scope}" is not a valid playlist scope.'
            f" Scope needs to be one of the following: {humanize_list(valid_scopes)}"
        )

    if scope in ["GLOBAL", "BOT"]:
        scope = PlaylistScope.GLOBAL.value
    elif scope in ["GUILD", "SERVER"]:
        scope = PlaylistScope.GUILD.value
    elif scope in ["USER", "MEMBER", "AUTHOR"]:
        scope = PlaylistScope.USER.value

    return scope


def humanize_scope(scope, ctx=None):

    if scope == PlaylistScope.GLOBAL.value:
        return ctx.name if ctx else "Global"
    elif scope == PlaylistScope.GUILD.value:
        return ctx.name if ctx else "Server"
    elif scope == PlaylistScope.USER.value:
        return str(ctx) if ctx else "User"


def _prepare_config_scope(
    scope, author: Optional[int] = None, guild: Optional[discord.Guild] = None
):
    scope = standardize_scope(scope)

    if scope == PlaylistScope.GLOBAL.value:
        config_scope = [PlaylistScope.GLOBAL.value]
    elif scope == PlaylistScope.USER.value:
        if author is None:
            raise MissingAuthor("Invalid author for user scope.")
        config_scope = [PlaylistScope.USER.value, str(getattr(author, "id", author))]
    else:
        if guild is None:
            raise MissingGuild("Invalid guild for guild scope.")
        config_scope = [PlaylistScope.GUILD.value, str(getattr(guild, "id", guild))]
    return config_scope


class Playlist:
    """A single playlist."""

    def __init__(
        self,
        bot: Red,
        scope: str,
        author: int,
        playlist_id: int,
        name: str,
        playlist_url: Optional[str] = None,
        tracks: Optional[List[dict]] = None,
        guild: Optional[discord.Guild] = None,
    ):
        self.bot = bot
        self.guild = guild
        self.scope = standardize_scope(scope)
        self.config_scope = _prepare_config_scope(self.scope, author, guild)
        self.author = author
        self.id = playlist_id
        self.name = name
        self.url = playlist_url
        self.tracks = tracks or []
        self.tracks_obj = [lavalink.Track(data=track) for track in self.tracks]

    async def edit(self, data: dict):
        """
        Edits a Playlist.
        Parameters
        ----------
        data: dict
            The attributes to change.
        """
        # Disallow ID editing
        if "id" in data:
            raise NotAllowed("Playlist ID cannot be edited.")

        for item in list(data.keys()):
            setattr(self, item, data[item])

        await _config.custom(*self.config_scope, str(self.id)).set(self.to_json())

    def to_json(self) -> dict:
        """Transform the object to a dict.
        Returns
        -------
        dict
            The playlist in the form of a dict.
        """
        data = dict(
            id=self.id,
            author=self.author,
            name=self.name,
            playlist_url=self.url,
            tracks=self.tracks,
        )

        return data

    @classmethod
    async def from_json(cls, bot: Red, scope: str, playlist_number: int, data: dict, **kwargs):
        """Get a Playlist object from the provided information.
        Parameters
        ----------
        bot: Red
            The bot's instance. Needed to get the target user.
        scope:str
            The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
        playlist_number: int
            The playlist's number.
        data: dict
            The JSON representation of the playlist to be gotten.
        **kwargs
            Extra attributes for the Playlist instance which override values
            in the data dict. These should be complete objects and not
            IDs, where possible.
        Returns
        -------
        Playlist
            The playlist object for the requested playlist.
        Raises
        ------
        `InvalidPlaylistScope`
            Passing a scope that is not supported.
        `MissingGuild`
            Trying to access the Guild scope without a guild.
        `MissingAuthor`
            Trying to access the User scope without an user id.
        """
        guild = kwargs.get("guild")
        author = data.get("author")
        playlist_id = data.get("id") or playlist_number
        name = data.get("name", "Unnamed")
        playlist_url = data.get("playlist_url", None)
        tracks = data.get("tracks", [])

        return cls(
            bot=bot,
            guild=guild,
            scope=scope,
            author=author,
            playlist_id=playlist_id,
            name=name,
            playlist_url=playlist_url,
            tracks=tracks,
        )


async def get_playlist(
    playlist_number: int,
    scope: str,
    bot: Red,
    guild: Optional[discord.Guild] = None,
    author: Optional[int] = None,
) -> Playlist:
    """
    Gets the playlist with the associated playlist number.
    Parameters
    ----------
    playlist_number: int
        The playlist number for the playlist to get.
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.
    bot: Red
        The bot's instance.
    Returns
    -------
    Playlist
        The playlist associated with the playlist number.
    Raises
    ------
    `RuntimeError`
        If there is no playlist for the specified number.
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    playlist_data = await _config.custom(
        *_prepare_config_scope(scope, author, guild), str(playlist_number)
    ).all()
    if not playlist_data["id"]:
        raise RuntimeError(f"That playlist does not exist for the following scope: {scope}")
    return await Playlist.from_json(
        bot, scope, playlist_number, playlist_data, guild=guild, author=author
    )


async def get_all_playlist(
    scope: str, bot: Red, guild: Optional[discord.Guild] = None, author: Optional[int] = None
) -> List[Playlist]:
    """
    Gets all playlist for the specified scope.
    Parameters
    ----------
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.
    bot: Red
        The bot's instance
    Returns
    -------
    list
        A list of all playlists for the specified scope
     Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    playlists = await _config.custom(*_prepare_config_scope(scope, author, guild)).all()
    return [
        await Playlist.from_json(
            bot, scope, playlist_number, playlist_data, guild=guild, author=author
        )
        for playlist_number, playlist_data in playlists.items()
    ]


async def create_playlist(
    ctx: commands.Context,
    scope: str,
    playlist_name: str,
    playlist_url: Optional[str] = None,
    tracks: Optional[List[dict]] = None,
    author: Optional[discord.User] = None,
    guild: Optional[discord.Guild] = None,
) -> Optional[Playlist]:
    """
    Creates a new Playlist.

    Parameters
    ----------
    ctx: commands.Context
        The context in which the play list is being created.
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    playlist_name: str
        The name of the new playlist.
    playlist_url:str
        the url of the new playlist.
    tracks: List[dict]
        A list of tracks to add to the playlist.
    author: discord.User
        The Author of the playlist.
        If provided it will create a playlist under this user.
        This is only required when creating a playlist in User scope.
    guild: discord.Guild
        The guild to create this playlist under.
         This is only used when creating a playlist in the Guild scope

    Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """

    playlist = Playlist(
        ctx.bot, scope, author.id, ctx.message.id, playlist_name, playlist_url, tracks, ctx.guild
    )

    await _config.custom(*_prepare_config_scope(scope, author.id, guild), str(ctx.message.id)).set(
        playlist.to_json()
    )
    return playlist


async def reset_playlist(
    scope: str, guild: Optional[discord.Guild] = None, author: Optional[int] = None
) -> None:
    """
    Wipes all playlists for the specified scope.

    Parameters
    ----------
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.

     Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    await _config.custom(*_prepare_config_scope(scope, author, guild)).clear()


async def delete_playlist(
    scope: str,
    playlist_id: Union[str, int],
    guild: Optional[discord.Guild] = None,
    author: Optional[Union[discord.abc.User, int]] = None,
) -> None:
    """
        Deletes the specified playlist.

        Parameters
        ----------
        scope: str
            The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
        playlist_id: Union[str, int]
            The ID of the playlist.
        guild: discord.Guild
            The guild to get the playlist from if scope is GUILDPLAYLIST.
        author: int
            The ID of the user to get the playlist from if scope is USERPLAYLIST.

         Raises
        ------
        `InvalidPlaylistScope`
            Passing a scope that is not supported.
        `MissingGuild`
            Trying to access the Guild scope without a guild.
        `MissingAuthor`
            Trying to access the User scope without an user id.
        """
    await _config.custom(*_prepare_config_scope(scope, author, guild), str(playlist_id)).clear()
