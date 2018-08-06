import discord
from collections import Iterable


class MessagePredicate:
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
    ctx
        Context object.
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

    def __init__(self, ctx, collection: Iterable = None, length: int = None, value=None):
        self.ctx = ctx
        self.collection = collection
        self.length = length
        self.value = value

    def valid_source(self, m):
        return self.same(m) and self.channel(m)

    def same(self, m):
        """Checks if the author of the message is the same as the command issuer."""
        return self.ctx.author == m.author

    def channel(self, m):
        """Verifies the message was sent from the same channel."""
        return self.ctx.channel == m.channel

    def cancelled(self, m):
        if self.valid_source(m) and m.content.lower() == f"{self.ctx.prefix}cancel":
            raise RuntimeError

    def confirm(self, m):
        """Checks if the author of the message is the same as the command issuer."""
        return self.valid_source(m) and m.content.lower() in ("yes", "no", "y", "n")

    def valid_int(self, m):
        """Returns true if the message content is an integer."""
        return self.valid_source(m) and m.content.isdigit()

    def valid_float(self, m):
        """Returns true if the message content is a float."""
        try:
            return self.valid_source(m) and float(m.content) >= 1
        except ValueError:
            return False

    def positive(self, m):
        """Returns true if the message content is an integer and is positive"""
        return self.valid_source(m) and m.content.isdigit() and int(m.content) >= 0

    def valid_role(self, m):
        """Returns true if the message content is an existing role on the server."""
        if self.valid_source(m):
            if discord.utils.get(self.ctx.guild.roles, name=m.content) is not None:
                return True
            elif discord.utils.get(self.ctx.guild.roles, id=m.content) is not None:
                return True
            else:
                return False
        else:
            return False

    def has_role(self, m):
        """Returns true if the message content is a role the message sender has."""
        if self.valid_source(m):
            if discord.utils.get(self.ctx.roles, name=m.content) is not None:
                return True
            elif discord.utils.get(self.ctx.roles, id=m.content) is not None:
                return True
            else:
                return False
        else:
            return False

    def equal(self, m):
        """Returns true if the message content is equal to the value set."""
        return self.valid_source(m) and m.content.lower() == self.value.lower()

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
            self.valid_source(m)
            and discord.utils.get(self.ctx.guild.members, name=m.content) is not None
        )

    def length_less(self, m):
        """Returns true if the message content length is less than the provided length."""
        try:
            return self.valid_source(m) and len(m.content) <= self.length
        except TypeError:
            raise ValueError("A length must be specified in Predicate().")

    def length_greater(self, m):
        """Returns true if the message content length is greater than or equal
           to the provided length."""
        try:
            return self.valid_source(m) and len(m.content) >= self.length
        except TypeError:
            raise ValueError("A length must be specified in Predicate().")

    def contained(self, m):
        """Returns true if the message content is a member of the provided collection."""
        try:
            return self.valid_source(m) and m.content.lower() in self.collection
        except TypeError:
            raise ValueError("An iterable was not specified in Predicate().")
