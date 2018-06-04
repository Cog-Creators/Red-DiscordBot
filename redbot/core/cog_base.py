from redbot.core import rpc


class CogBase:
    __rpc_methods = []

    def add_rpc_methods(self, *methods, prefix: str = None):
        to_add = [m for m in methods if m not in self.__rpc_methods]

        if prefix is None:
            prefix = self.__class__.__name__.lower()

        rpc.server.add_multi_method(*to_add, prefix=prefix)
        self.__rpc_methods.extend(to_add)

    def cleanup(self):
        for meth in self.__rpc_methods:
            rpc.server.remove_method(meth)

        rpc.server.remove_methods(self.__class__.__name__.lower())
