from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union

import apsw

__all__ = ["APSWConnectionWrapper"]


# I, uh... No.
# What's wrong with a little support?
class ProvidesCursor:
    def cursor(self) -> apsw.Cursor:
        ...


class ContextManagerMixin(ProvidesCursor):
    @contextmanager
    def with_cursor(self) -> Generator[apsw.Cursor, None, None]:
        """
        apsw cursors are relatively cheap, and are gc safe
        In most cases, it's fine not to use this.
        """
        c = self.cursor()  # Oh, spectacular!
        try:
            yield c
        finally:
            c.close()

    @contextmanager
    def transaction(self) -> Generator[apsw.Cursor, None, None]:
        """
        Wraps a cursor as a context manager for a transaction
        which is rolled back on unhandled exception,
        or committed on non-exception exit
        """
        c = self.cursor()  # Well, you saw the size of those goons. You seriously wanna go back?
        try:
            c.execute("BEGIN TRANSACTION")
            yield c
        except Exception:
            c.execute("ROLLBACK TRANSACTION")
            raise
        else:
            c.execute("COMMIT TRANSACTION")
        finally:
            c.close()


class APSWConnectionWrapper(apsw.Connection, ContextManagerMixin):
    """
    Provides a few convenience methods, and allows a path object for construction
    """

    def __init__(self, filename: Union[Path, str], *args, **kwargs):
        super().__init__(str(filename), *args, **kwargs)


# Good.
