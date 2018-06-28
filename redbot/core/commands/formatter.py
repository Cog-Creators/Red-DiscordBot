import discord
from discord.ext.commands import formatter
from . import commands
from redbot.core import checks
import asyncio


class HelpFormatter(formatter.HelpFormatter):
    """
    Custom override to discord.py's help formatter
    """

    def __init__(self, *args, **kwargs):
        self.context = None
        self.command = None
        super(HelpFormatter, self).__init__(*args, **kwargs)

    async def filter_command_list(self):
        """Returns a filtered list of commands based on the two attributes
        provided, :attr:`show_check_failure` and :attr:`show_hidden`.
        Also filters based on if :meth:`~.HelpFormatter.is_cog` is valid.
        Returns
        --------
        iterable
            An iterable with the filter being applied. The resulting value is
            a (key, value) :class:`tuple` of the command name and the command itself.
        """

        permissions_cog = self.context.get_cog('Permissions')
        if permissions_cog:
            permissions_dict = await permissions_cog.get_user_ctx_overrides(self.context)
        else:
            permissions_dict = {'allowed': [], 'denied': []}

        is_admin = await checks.is_admin_or_superior(self.context)
        is_mod = await checks.is_mod_or_superior(self.context)
        is_owner = await self.context.bot.is_owner(self.context.author)
        is_guild_owner = self.context.author == self.context.guild.owner if self.context.guild else is_owner

        def sane_no_suspension_point_predicate(tup):
            cmd = tup[1]
            if self.is_cog():
                # filter commands that don't exist to this cog.
                if cmd.instance is not self.command:
                    return False

            if cmd.hidden and not self.show_hidden:
                return False

            return True

        async def process_closure(check_obj) -> bool:
            """
            Takes a check object, returns the permission resolution section of it
            """
            to_check = {}
            if not hasattr(check_obj, '__closure__'):
                return False
            for cell_object in check_obj.__closure__:
                for contents in cell_object.cell_contents:
                    to_check.update(contents)
            return await checks.check_permissions(self.context, to_check)

        async def special_check_handling(com) -> bool:
            """
            This exists to expedite handling of permissions cog interactions
            """
            for check in com.checks:
                if check.__module__ == 'redbot.core.checks' and any(
                        x in str(check) for x in ('owner', 'admin', 'mod')
                ):
                    if com in permissions_dict['allowed']:
                        continue
                    if com in permissions_dict['denied']:
                        return False
                    if 'owner' in str(check):
                        if is_owner:
                            continue
                    elif 'guildowner' in str(check):
                        if is_guild_owner:
                            continue
                    elif 'admin' in str(check):
                        if is_admin:
                            continue
                    elif 'mod' in str(check):
                        if is_mod:
                            continue
                    if await process_closure(check):
                        continue
                    return False
                else:  # Still need to process other checks too
                    ret = await discord.utils.maybe_coroutine(check, self.context)
                    if not ret:
                        return False
            # local checks
            cog = com.instance
            if cog is not None:
                try:
                    local_check = getattr(cog, '_{0.__class__.__name__}__local_check'.format(cog))
                except AttributeError:
                    pass
                else:
                    ret = await discord.utils.maybe_coroutine(local_check, self.context)
                    if not ret:
                        return False
            # Finally, global check handling
            return await self.context.bot.can_run(self.context)
                    
        async def predicate(tup):
            if sane_no_suspension_point_predicate(tup) is False:
                return False
            com = tup[1]
            try:
                return (await special_check_handling(com))
            except commands.CommandError:
                return False

        iterator = self.command.all_commands.items() if not self.is_cog() else self.context.bot.all_commands.items()
        if self.show_check_failure:
            return filter(sane_no_suspension_point_predicate, iterator)

        # Gotta run every check and verify it
        ret = []
        for elem in iterator:
            valid = await predicate(elem)
            if valid:
                ret.append(elem)
        return ret