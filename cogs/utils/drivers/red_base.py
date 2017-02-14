class BaseDriver:
    def get_global(self, cog_name, ident, collection_id, key, *, default=None):
        raise NotImplementedError()

    def get_server(self, cog_name, ident, server_id, key, *, default=None):
        raise NotImplementedError()

    def get_channel(self, cog_name, ident, channel_id, key, *, default=None):
        raise NotImplementedError()

    def get_role(self, cog_name, ident, role_id, key, *, default=None):
        raise NotImplementedError()

    def get_member(self, cog_name, ident, user_id, server_id, key, *,
                   default=None):
        raise NotImplementedError()

    def get_user(self, cog_name, ident, user_id, key, *, default=None):
        raise NotImplementedError()

    def get_misc(self, cog_name, ident, *, default=None):
        raise NotImplementedError()

    def set_global(self, cog_name, ident, key, value, clear=False):
        raise NotImplementedError()

    def set_server(self, cog_name, ident, server_id, key, value, clear=False):
        raise NotImplementedError()

    def set_channel(self, cog_name, ident, channel_id, key, value,
                    clear=False):
        raise NotImplementedError()

    def set_role(self, cog_name, ident, role_id, key, value, clear=False):
        raise NotImplementedError()

    def set_member(self, cog_name, ident, user_id, server_id, key, value,
                   clear=False):
        raise NotImplementedError()

    def set_user(self, cog_name, ident, user_id, key, value, clear=False):
        raise NotImplementedError()

    def set_misc(self, cog_name, ident, value, clear=False):
        raise NotImplementedError()
