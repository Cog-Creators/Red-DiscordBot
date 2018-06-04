import typing

if typing.TYPE_CHECKING:
    from redbot.core.bot import Red


class CogBase:
    def __init__(self, bot: "Red"):
        self.__bot = bot
        self.__rpc_methods = []

    def add_rpc_methods(self, *methods, prefix: str = None):
        to_add = [m for m in methods if m not in self.__rpc_methods]

        if prefix is None:
            prefix = self.__class__.__name__.lower()

        self.__bot.rpc.add_multi_method(*to_add, prefix=prefix)
        self.__rpc_methods.extend(to_add)

    def __unload(self):
        for meth in self.__rpc_methods:
            self.__bot.rpc.remove_method(meth)

        self.__bot.rpc.remove_methods(self.__class__.__name__.lower())
