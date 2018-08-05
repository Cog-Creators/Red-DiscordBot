import discord
from collections import Iterable


class Predicate:
    """A simple collection of predicates.

    These predicates were made to help simplify checks in message events and
    reduce boilerplate code.

    For examples:
    # valid yes or no response
    `ctx.bot.wait_for('message', timeout=15.0, check=Predicate(ctx).confirm)`

    # check if message content in under 2000 characters
    `check = Predicate(ctx, length=2000).length_under
     ctx.bot.wait_for('message', timeout=15.0, check=check)`


    Attributes
    ----------
    sender : `discord.Member`
        Used to verify the message content is coming from the desired sender.
    collection : `Iterable`
        Optional argument used for checking if the message content is inside the
        declared collection.
    length : `int`
        Optional argument for comparing message lengths.
    value
         Optional argument that can be either a string, int, float, or object.
         Used for comparison and equality.

    Returns
    -------
        Boolean or it will raise a ValueError if you use a certain methods without an argument or
        the value argument is set to an invalid type for a particular method.

    """

    def __init__(
        self, sender: discord.Member, collection: Iterable = None, length: int = None, value=None
    ):
        self.sender = sender
        self.collection = collection
        self.length = length
        self.value = value

    def same(self, m):
        """Checks if the author of the message is the same as the command issuer."""
        return self.sender.author == m.author

    def confirm(self, m):
        """Checks if the author of the message is the same as the command issuer."""
        return self.same(m) and m.content.lower() in ("yes", "no", "y", "n")

    def valid_int(self, m):
        """Returns true if the message content is an integer."""
        return self.same(m) and m.content.isdigit()

    def valid_float(self, m):
        """Returns true if the message content is a float."""
        try:
            return self.same(m) and float(m.content) >= 1
        except ValueError:
            return False

    def positive(self, m):
        """Returns true if the message content is an integer and is positive"""
        return self.same(m) and m.content.isdigit() and int(m.content) >= 0

    def valid_role(self, m):
        """Returns true if the message content is an existing role on the server."""
        return (
            self.same(m) and discord.utils.get(self.sender.guild.roles, name=m.content) is not None
        )

    def has_role(self, m):
        """Returns true if the message content is a role the message sender has."""
        return self.same(m) and discord.utils.get(self.sender.roles, name=m.content) is not None

    def equal(self, m):
        """Returns true if the message content is equal to the value set."""
        return self.same(m) and m.content.lower() == self.value.lower()

    def greater(self, m):
        """Returns true if the message content is greater than the value set."""
        try:
            return self.valid_int(m) or self.valid_float(m) and float(m.content) > int(self.value)
        except TypeError:
            raise ValueError("Value argument in Predicate() must be an integer or float.")

    def less(self, m):
        """Returns true if the message content is less than the value set."""
        try:
            return self.valid_int(m) or self.valid_float(m) and float(m.content) < int(self.value)
        except TypeError:
            raise ValueError("Value argument in Predicate() must be an integer or float.")

    def member(self, m):
        """Returns true if the message content is the name of a member in the server."""
        return (
            self.same(m)
            and discord.utils.get(self.sender.guild.members, name=m.content) is not None
        )

    def length_less(self, m):
        """Returns true if the message content length is less than the provided length."""
        try:
            return self.same(m) and len(m.content) <= self.length
        except TypeError:
            raise ValueError("A length must be specified in Predicate().")

    def length_greater(self, m):
        """Returns true if the message content length is greater than or equal
           to the provided length."""
        try:
            return self.same(m) and len(m.content) >= self.length
        except TypeError:
            raise ValueError("A length must be specified in Predicate().")

    def contained(self, m):
        """Returns true if the message content is a member of the provided collection."""
        try:
            return self.same(m) and m.content in self.collection
        except TypeError:
            raise ValueError("An iterable was not specified in Predicate().")
