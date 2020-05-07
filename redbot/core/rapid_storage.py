from rapid_dev_storage import SQLiteBackend, Storage, StoredValue, StorageGroup, NoValue
import discord

from .data_manager import cog_data_path

__all__ = ["RapidStorage", "StorageGroup", "StoredValue", "NoValue"]


class RapidStorage(Storage):

    @classmethod
    async def get_cog_storage(cls, cog_name: str, unique_identifier: int):

        path = cog_data_path(raw_name=cog_name) / "rapid_storage.db"
        backend = await SQLiteBackend.create_backend_instance(path, cog_name, unique_identifier)
        return cls(backend)

    @property
    def botwide(self) -> StorageGroup:
        return self.get_group("RED_BOTWIDE")

    @property
    def guild_group(self) -> StorageGroup:
        return self.get_group("RED_GUILD")

    @property
    def user_group(self) -> StorageGroup:
        return self.get_group("RED_USER")

    @property
    def member_group(self) -> StorageGroup:
        return self.get_group("RED_MEMBER")

    @property
    def role_group(self) -> StorageGroup:
        return self.get_group("RED_ROLE")

    @property
    def channel_group(self) -> StorageGroup:
        return self.get_group("RED_ANY_CHANNEL")

    def member(self, member: discord.Member) -> StoredValue:
        return self.get_group("RED_MEMBER")[f"{member.guild.id}", f"{member.id}"]

    def user(self, user: discord.User) -> StoredValue:
        return self.get_group("RED_USER")[f"{user.id}"]

    def channel(self, channel) -> StoredValue:
        return self.get_group("RED_ANY_CHANNEL")[f"{channel.id}"]

    def guild(self, guild: discord.Guild) -> StoredValue:
        return self.get_group("RED_GUILD")[f"{guild.id}"]

    def role(self, role: discord.Role) -> StoredValue:
        return self.get_group("RED_ROLE")[f"{role.id}"]
