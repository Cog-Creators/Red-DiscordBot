class BaseDriver:
    def get_global(self, cog_name, ident, collection_id, key, *, default=None):
        raise NotImplementedError()

    def get_guild(self, cog_name, ident, guild_id, key, *, default=None):
        raise NotImplementedError()

    def get_channel(self, cog_name, ident, channel_id, key, *, default=None):
        raise NotImplementedError()

    def get_role(self, cog_name, ident, role_id, key, *, default=None):
        raise NotImplementedError()

    def get_member(self, cog_name, ident, user_id, guild_id, key, *,
                   default=None):
        raise NotImplementedError()

    def get_user(self, cog_name, ident, user_id, key, *, default=None):
        raise NotImplementedError()

    def get_misc(self, cog_name, ident, *, default=None):
        raise NotImplementedError()

    def set_global(self, cog_name, ident, key, value, clear=False):
        raise NotImplementedError()

    def set_guild(self, cog_name, ident, guild_id, key, value, clear=False):
        raise NotImplementedError()

    async def set_channel(self, cog_name, ident, channel_id, key, value,
                          clear=False):
        raise NotImplementedError()

    async def set_role(self, cog_name, ident, role_id, key, value, clear=False):
        raise NotImplementedError()

    async def set_member(self, cog_name, ident, user_id, guild_id, key, value,
                   clear=False):
        raise NotImplementedError()

    async def set_user(self, cog_name, ident, user_id, key, value, clear=False):
        raise NotImplementedError()

    async def set_misc(self, cog_name, ident, value, clear=False):
        raise NotImplementedError()
