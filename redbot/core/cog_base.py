from redbot.core import rpc


class CogBase:
    def __init__(self):
        self.__rpc_methods = []

    def __add_rpc_methods(self, *methods):
        to_add = [m for m in methods if m not in self.__rpc_methods]
        prefix = self.__class__.__name__.lower()

        rpc.add_multi_method(*to_add, prefix=prefix)
        self.__rpc_methods.extend(to_add)

    def __cleanup(self):
        for meth in self.__rpc_methods:
            rpc.remove_method(meth)

        rpc.remove_methods(self.__class__.__name__.lower())
