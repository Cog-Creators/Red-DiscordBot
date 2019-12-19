import json
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum, unique
from typing import List, Optional, Union

import apsw
import discord
import lavalink

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list
from .errors import InvalidPlaylistScope, MissingAuthor, MissingGuild, NotAllowed

_config: Config = None
_bot: Red = None
database: "Database" = None

__all__ = [
    "Playlist",
    "PlaylistScope",
    "get_playlist",
    "get_all_playlist",
    "create_playlist",
    "reset_playlist",
    "delete_playlist",
    "humanize_scope",
    "standardize_scope",
    "FakePlaylist",
    "get_all_playlist_for_migration23",
    "database",
]

FakePlaylist = namedtuple("Playlist", "author scope")

_ = Translator("Audio", __file__)

_PRAGMA_UPDATE_temp_store = """
PRAGMA temp_store = 2;
"""
_PRAGMA_UPDATE_journal_mode = """
PRAGMA journal_mode = wal;
"""
_PRAGMA_UPDATE_read_uncommitted = """
PRAGMA read_uncommitted = 1;
"""

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS playlists ( 
    scope_type INTEGER NOT NULL, 
    playlist_id INTEGER NOT NULL, 
    playlist_name TEXT NOT NULL, 
    scope_id INTEGER NOT NULL, 
    author_id INTEGER NOT NULL, 
    playlist_url TEXT, 
    tracks BLOB, 
    PRIMARY KEY (playlist_id, scope_id, scope_type)
);
"""

_DELETE = """
DELETE
FROM
    playlists 
WHERE
    (
        scope_type = :scope_type 
        AND playlist_id = :playlist_id 
        AND scope_id = :scope_id 
    )
;
"""
_DELETE_SCOPE = """
DELETE
FROM
    playlists 
WHERE
    scope_type = :scope_type ;
"""

_FETCH_ALL = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    scope_type = :scope_type 
    AND scope_id = :scope_id
    ;
"""

_FETCH_ALL_WITH_FILTER = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    (
        scope_type = :scope_type 
        AND scope_id = :scope_id
        AND author_id = :author_id 
    )
;
"""

_FETCH_ALL_CONVERTER = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    (
        scope_type = :scope_type 
        AND
        (
        playlist_id = :playlist_id
        OR
        LOWER(playlist_name) LIKE "%" || COALESCE(LOWER(:playlist_name), "") || "%"
        )
    )
;
"""

_FETCH = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    (
        scope_type = :scope_type 
        AND playlist_id = :playlist_id 
        AND scope_id = :scope_id 
    )
"""

_UPSET = """
INSERT INTO
    playlists ( scope_type, playlist_id, playlist_name, scope_id, author_id, playlist_url, tracks ) 
VALUES
    (
        :scope_type, :playlist_id, :playlist_name, :scope_id, :author_id, :playlist_url, :tracks 
    )
    ON CONFLICT (scope_type, playlist_id, scope_id) DO 
    UPDATE
    SET
        playlist_name = excluded.playlist_name, 
        playlist_url = excluded.playlist_url, 
        tracks = excluded.tracks;
"""
_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS name_index ON playlists (scope_type, playlist_id, playlist_name, scope_id);
"""


@dataclass
class SQLFetchResult:
    playlist_id: int
    playlist_name: str
    scope_id: int
    author_id: int
    playlist_url: Optional[str] = None
    tracks: str = "[]"


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


class Database:
    def __init__(self):
        self._database = apsw.Connection(str(cog_data_path(_bot.get_cog("Audio")) / "Audio.db"))
        self.cursor = self._database.cursor()
        self.cursor.execute(_PRAGMA_UPDATE_temp_store)
        self.cursor.execute(_PRAGMA_UPDATE_journal_mode)
        self.cursor.execute(_PRAGMA_UPDATE_read_uncommitted)
        self.cursor.execute(_CREATE_TABLE)
        self.cursor.execute(_CREATE_INDEX)

    def close(self):
        self._database.close()

    @staticmethod
    def get_scope_type(scope: str) -> int:
        if scope == PlaylistScope.GLOBAL.value:
            table = 1
        elif scope == PlaylistScope.USER.value:
            table = 3
        else:
            table = 2
        return table

    def fetch(self, scope: str, playlist_id: int, scope_id: int) -> SQLFetchResult:
        scope_type = self.get_scope_type(scope)
        row = (
            self.cursor.execute(
                _FETCH,
                ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type}),
            ).fetchone()
            or []
        )

        return SQLFetchResult(*row) if row else None

    def fetch_all(self, scope: str, scope_id: int, author_id=None) -> List[SQLFetchResult]:
        scope_type = self.get_scope_type(scope)
        if author_id is not None:
            output = self.cursor.execute(
                _FETCH_ALL_WITH_FILTER,
                ({"scope_type": scope_type, "scope_id": scope_id, "author_id": author_id}),
            ).fetchall()
        else:
            output = self.cursor.execute(
                _FETCH_ALL, ({"scope_type": scope_type, "scope_id": scope_id})
            ).fetchall()
        return [SQLFetchResult(*row) for row in output] if output else []

    def fetch_all_converter(self, scope: str, playlist_name, playlist_id) -> List[SQLFetchResult]:
        scope_type = self.get_scope_type(scope)
        try:
            playlist_id = int(playlist_id)
        except:
            playlist_id = -1
        output = (
            self.cursor.execute(
                _FETCH_ALL_CONVERTER,
                (
                    {
                        "scope_type": scope_type,
                        "playlist_name": playlist_name,
                        "playlist_id": playlist_id,
                    }
                ),
            ).fetchall()
            or []
        )
        return [SQLFetchResult(*row) for row in output] if output else []

    def delete(self, scope: str, playlist_id: int, scope_id: int):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(
            _DELETE, ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type})
        )

    def drop(self, scope: str):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(_DELETE_SCOPE, ({"scope_type": scope_type}))

    def create_table(self, scope: str):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(_CREATE_TABLE, ({"scope_type": scope_type}))

    def upsert(
        self,
        scope: str,
        playlist_id: int,
        playlist_name: str,
        scope_id: int,
        author_id: int,
        playlist_url: str,
        tracks: List[dict],
    ):
        scope_type = self.get_scope_type(scope)
        self.cursor.execute(
            _UPSET,
            (
                {
                    "scope_type": str(scope_type),
                    "playlist_id": int(playlist_id),
                    "playlist_name": str(playlist_name),
                    "scope_id": int(scope_id),
                    "author_id": int(author_id),
                    "playlist_url": playlist_url,
                    "tracks": json.dumps(tracks),
                }
            ),
        )


def _pass_config_to_playlist(config: Config, bot: Red):
    global _config, _bot, database
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot
    if database is None:
        database = Database()


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


def humanize_scope(scope, ctx=None, the=None):

    if scope == PlaylistScope.GLOBAL.value:
        return ctx or _("the ") if the else "" + _("Global")
    elif scope == PlaylistScope.GUILD.value:
        return ctx.name if ctx else _("the ") if the else "" + _("Server")
    elif scope == PlaylistScope.USER.value:
        return str(ctx) if ctx else _("the ") if the else "" + _("User")


def _prepare_config_scope(
    scope, author: Union[discord.abc.User, int] = None, guild: discord.Guild = None
):
    scope = standardize_scope(scope)

    if scope == PlaylistScope.GLOBAL.value:
        config_scope = [PlaylistScope.GLOBAL.value, _bot.user.id]
    elif scope == PlaylistScope.USER.value:
        if author is None:
            raise MissingAuthor("Invalid author for user scope.")
        config_scope = [PlaylistScope.USER.value, getattr(author, "id", author)]
    else:
        if guild is None:
            raise MissingGuild("Invalid guild for guild scope.")
        config_scope = [PlaylistScope.GUILD.value, getattr(guild, "id", guild)]
    return config_scope


def _prepare_config_scope_for_migration23(  # TODO: remove me in a future version ?
    scope, author: Union[discord.abc.User, int] = None, guild: discord.Guild = None
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


class PlaylistMigration23:  # TODO: remove me in a future version ?
    """A single playlist."""

    def __init__(
        self,
        scope: str,
        author: int,
        playlist_id: int,
        name: str,
        playlist_url: Optional[str] = None,
        tracks: Optional[List[dict]] = None,
        guild: Union[discord.Guild, int, None] = None,
    ):
        self.guild = guild
        self.scope = standardize_scope(scope)
        self.author = author
        self.id = playlist_id
        self.name = name
        self.url = playlist_url
        self.tracks = tracks or []

    @classmethod
    async def from_json(
        cls, scope: str, playlist_number: int, data: dict, **kwargs
    ) -> "PlaylistMigration23":
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
        guild = data.get("guild") or kwargs.get("guild")
        author = data.get("author")
        playlist_id = data.get("id") or playlist_number
        name = data.get("name", "Unnamed")
        playlist_url = data.get("playlist_url", None)
        tracks = data.get("tracks", [])

        return cls(
            guild=guild,
            scope=scope,
            author=author,
            playlist_id=playlist_id,
            name=name,
            playlist_url=playlist_url,
            tracks=tracks,
        )

    async def save(self):
        """
        Saves a Playlist to SQL.
        """
        scope, scope_id = _prepare_config_scope(self.scope, self.author, self.guild)
        database.upsert(
            scope,
            playlist_id=int(self.id),
            playlist_name=self.name,
            scope_id=scope_id,
            author_id=self.author,
            playlist_url=self.url,
            tracks=self.tracks,
        )


async def get_all_playlist_for_migration23(  # TODO: remove me in a future version ?
    scope: str,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
) -> List[PlaylistMigration23]:
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
    specified_user:bool
        Whether or not user ID was passed as an argparse.
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
    playlists = await _config.custom(scope).all()
    if scope == PlaylistScope.GLOBAL.value:
        return [
            await PlaylistMigration23.from_json(
                scope,
                playlist_number,
                playlist_data,
                guild=guild,
                author=int(playlist_data.get("author", 0)),
            )
            for playlist_number, playlist_data in playlists.items()
        ]
    elif scope == PlaylistScope.USER.value:
        return [
            await PlaylistMigration23.from_json(
                scope, playlist_number, playlist_data, guild=guild, author=int(user_id)
            )
            for user_id, scopedata in playlists.items()
            for playlist_number, playlist_data in scopedata.items()
        ]
    else:
        return [
            await PlaylistMigration23.from_json(
                scope,
                playlist_number,
                playlist_data,
                guild=int(guild_id),
                author=int(playlist_data.get("author", 0)),
            )
            for guild_id, scopedata in playlists.items()
            for playlist_number, playlist_data in scopedata.items()
        ]


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
        guild: Union[discord.Guild, int, None] = None,
    ):
        self.bot = bot
        self.guild = guild
        self.scope = standardize_scope(scope)
        self.config_scope = _prepare_config_scope(self.scope, author, guild)
        self.scope_id = self.config_scope[-1]
        self.author = author
        self.author_id = getattr(self.author, "id", self.author)
        self.guild_id = (
            getattr(guild, "id", guild) if self.scope == PlaylistScope.GLOBAL.value else None
        )
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
        await self.save()
        return self

    async def save(self):
        """
        Saves a Playlist.
        """
        scope, scope_id = self.config_scope
        database.upsert(
            scope,
            playlist_id=int(self.id),
            playlist_name=self.name,
            scope_id=scope_id,
            author_id=self.author_id,
            playlist_url=self.url,
            tracks=self.tracks,
        )

    def to_json(self) -> dict:
        """Transform the object to a dict.
        Returns
        -------
        dict
            The playlist in the form of a dict.
        """
        data = dict(
            id=self.id,
            author=self.author_id,
            guild=self.guild_id,
            name=self.name,
            playlist_url=self.url,
            tracks=self.tracks,
        )

        return data

    @classmethod
    async def from_json(
        cls, bot: Red, scope: str, playlist_number: int, data: SQLFetchResult, **kwargs
    ):
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
        guild = data.scope_id if scope == PlaylistScope.GUILD.value else kwargs.get("guild")
        author = data.author_id
        playlist_id = data.playlist_id or playlist_number
        name = data.playlist_name
        playlist_url = data.playlist_url
        tracks = json.loads(data.tracks)

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
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
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
    scope_standard, scope_id = _prepare_config_scope(scope, author, guild)
    playlist_data = database.fetch(scope_standard, playlist_number, scope_id)

    if not (playlist_data and playlist_data.playlist_id):
        raise RuntimeError(f"That playlist does not exist for the following scope: {scope}")
    return await Playlist.from_json(
        bot, scope_standard, playlist_number, playlist_data, guild=guild, author=author
    )


async def get_all_playlist(
    scope: str,
    bot: Red,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
    specified_user: bool = False,
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
    specified_user:bool
        Whether or not user ID was passed as an argparse.
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
    scope_standard, scope_id = _prepare_config_scope(scope, author, guild)

    if specified_user:
        user_id = getattr(author, "id", author)
        playlists = database.fetch_all(scope_standard, scope_id, author_id=user_id)
    else:
        playlists = database.fetch_all(scope_standard, scope_id)
    return [
        await Playlist.from_json(
            bot, scope, playlist.playlist_id, playlist, guild=guild, author=author
        )
        for playlist in playlists
    ]


async def get_all_playlist_converter(
    scope: str,
    bot: Red,
    arg: str,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
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
    specified_user:bool
        Whether or not user ID was passed as an argparse.
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
    scope_standard, scope_id = _prepare_config_scope(scope, author, guild)
    playlists = database.fetch_all_converter(scope_standard, playlist_name=arg, playlist_id=arg)
    return [
        await Playlist.from_json(
            bot, scope, playlist.playlist_id, playlist, guild=guild, author=author
        )
        for playlist in playlists
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
        ctx.bot,
        scope,
        author.id,
        ctx.message.id,
        playlist_name,
        playlist_url,
        tracks,
        guild or ctx.guild,
    )
    await playlist.save()
    return playlist


async def reset_playlist(
    scope: str,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
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
    scope, scope_id = _prepare_config_scope(scope, author, guild)
    database.drop(scope)
    database.create_table(scope)


async def delete_playlist(
    scope: str,
    playlist_id: Union[str, int],
    guild: discord.Guild,
    author: Union[discord.abc.User, int] = None,
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
    scope, scope_id = _prepare_config_scope(scope, author, guild)
    database.delete(scope, int(playlist_id), scope_id)
