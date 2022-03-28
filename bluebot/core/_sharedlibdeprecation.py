from importlib.abc import MetaPathFinder
import warnings


class SharedLibDeprecationWarning(DeprecationWarning):
    pass


warnings.simplefilter("always", SharedLibDeprecationWarning)


class SharedLibImportWarner(MetaPathFinder):
    """
    Deprecation warner for shared libraries. This class sits on `sys.meta_path`
    and prints warning if imported module is a shared library
    """

    def find_spec(self, fullname, path, target=None) -> None:
        """This is only supposed to print warnings, it won't ever return module spec."""
        parts = fullname.split(".")
        if parts[0] != "cog_shared" or len(parts) != 2:
            return None
        msg = (
            "One of the cogs uses shared libraries which are"
            " deprecated and scheduled for removal in the future.\n"
            "You should inform the author(s) of the cog about this message."
        )
        warnings.warn(msg, SharedLibDeprecationWarning, stacklevel=2)
        return None
