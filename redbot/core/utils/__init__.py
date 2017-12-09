__all__ = ['TYPE_CHECKING']

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

