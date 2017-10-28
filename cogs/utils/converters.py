from discord.ext.commands.converter import IDConverter
from discord.ext.commands.errors import BadArgument
import re


# This could've been imported but since it's an internal it's safer
# to get it here
def _get_from_servers(bot, getter, argument):
    result = None
    for server in bot.servers:
        result = getattr(server, getter)(argument)
        if result:
            return result
    return result


class GlobalUser(IDConverter):
    """
    This is an (almost) straight copy of discord.py's Member converter
    The key difference is that if the command is issued in a server it will
    first attempt to get the user from that server and upon failing it will
    attempt to fish it from the global pool
    """
    def convert(self):
        message = self.ctx.message
        bot = self.ctx.bot
        match = self._get_id_match() or re.match(r'<@!?([0-9]+)>$', self.argument)
        server = message.server
        result = None
        if match is None:
            # not a mention...
            if server:
                result = server.get_member_named(self.argument)
            if result is None:
                result = _get_from_servers(bot, 'get_member_named', self.argument)
        else:
            user_id = match.group(1)
            if server:
                result = server.get_member(user_id)
            if result is None:
                result = _get_from_servers(bot, 'get_member', user_id)

        if result is None:
            raise BadArgument('User "{}" not found'.format(self.argument))

        return result
