import discord
from typing import Dict

__all__ = ["OverwriteDiff"]


class OverwriteDiff:
    """
    Represents a change in PermissionOverwrites.

    All math operations done with the values contained are bitwise.

    This object is considered False for boolean logic when representing no change.

    Attributes
    ----------
    allows_added : int
    allows_removed : int
    denies_added : int
    denies_removed : int

    .. versionadded: 3.2.0
    """

    def __init__(self, **data: int):
        self.allows_added = data.pop("allows_added", 0)
        self.allows_removed = data.pop("allows_removed", 0)
        self.denies_added = data.pop("denies_added", 0)
        self.denies_removed = data.pop("denies_removed", 0)

        if (
            (self.allows_added & self.denies_added)
            or (self.allows_removed & self.denies_removed)
            or (self.allows_added & self.allows_removed)
            or (self.denies_added & self.denies_removed)
        ):
            raise ValueError(
                "It is impossible for this to be the difference of two valid overwrite objects."
            )

    def __repr__(self):
        return (
            f"<OverwriteDiff "
            f"allows_added={self.allows_added} allows_removed={self.allows_removed} "
            f"denies_added={self.denies_added} denies_removed={self.denies_removed}>"
        )

    def __bool__(self):
        return self.allows_added or self.allows_removed or self.denies_added or self.denies_removed

    def to_dict(self) -> Dict[str, int]:
        return {
            "allows_added": self.allows_added,
            "allows_removed": self.allows_removed,
            "denies_added": self.denies_added,
            "denies_removed": self.denies_removed,
        }

    def __radd__(self, other: discord.PermissionOverwrite) -> discord.PermissionOverwrite:
        if not isinstance(other, discord.PermissionOverwrite):
            return NotImplemented
        return self.apply_to_overwirte(other)

    def __rsub__(self, other: discord.PermissionOverwrite) -> discord.PermissionOverwrite:
        if not isinstance(other, discord.PermissionOverwrite):
            return NotImplemented
        return self.remove_from_overwrite(other)

    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        return cls(**data)

    @classmethod
    def from_overwrites(
        cls, before: discord.PermissionOverwrite, after: discord.PermissionOverwrite
    ):
        """
        Returns the difference between two permission overwrites.

        Parameters
        ----------
        before : discord.PermissionOverwrite
        after : discord.PermissionOverwrite
        """

        b_allow, b_deny = before.pair()
        a_allow, a_deny = after.pair()

        b_allow_val, b_deny_val = b_allow.value, b_deny.value
        a_allow_val, a_deny_val = a_allow.value, a_deny.value

        allows_added = a_allow_val & ~b_allow_val
        allows_removed = b_allow_val & ~a_allow_val

        denies_added = a_deny_val & ~b_deny_val
        denies_removed = b_deny_val & ~a_deny_val

        return cls(
            allows_added=allows_added,
            allows_removed=allows_removed,
            denies_added=denies_added,
            denies_removed=denies_removed,
        )

    def apply_to_overwirte(
        self, overwrite: discord.PermissionOverwrite
    ) -> discord.PermissionOverwrite:
        """
        Creates a new overwrite by applying a diff to existing overwrites.

        Parameters
        ----------
        overwrite : discord.PermissionOverwrite

        Returns
        -------
        discord.PermissionOverwrite
            A new overwrite object with the diff applied to it.
        """

        current_allow, current_deny = overwrite.pair()

        allow_value = (current_allow.value | self.allows_added) & ~self.allows_removed
        deny_value = (current_deny.value | self.denies_added) & ~self.denies_removed

        na = discord.Permissions(allow_value)
        nd = discord.Permissions(deny_value)
        return discord.PermissionOverwrite.from_pair(na, nd)

    def remove_from_overwrite(
        self, overwrite: discord.PermissionOverwrite
    ) -> discord.PermissionOverwrite:
        """
        If given the after for the current diff object, this should return the before.

        This can be used to roll back changes.

        Parameters
        ----------
        overwrite : discord.PermissionOverwrite

        Returns
        -------
        discord.PermissionOverwrite
            A new overwrite object with the diff removed from it.
        """
        current_allow, current_deny = overwrite.pair()

        allow_value = (current_allow.value | self.allows_removed) & ~self.allows_added
        deny_value = (current_deny.value | self.denies_removed) & ~self.denies_added

        na = discord.Permissions(allow_value)
        nd = discord.Permissions(deny_value)
        return discord.PermissionOverwrite.from_pair(na, nd)
