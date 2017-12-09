__all__ = ['TYPE_CHECKING', 'NewType']

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

try:
    from typing import NewType
except ImportError:
    def NewType(name, tp):
        return type(name, (tp,), {})
