import discord
from discord.ext.commands import formatter, CommandError
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

        # prep work for not manually calling the permissions cog individually per command
        permissions_cog = self.context.bot.get_cog("Permissions")
        if permissions_cog:
            permissions_dict = await permissions_cog.get_user_ctx_overrides(self.context)
        else:
            permissions_dict = {"allowed": [], "denied": []}

        is_admin = await checks.is_admin_or_superior(self.context)
        is_mod = await checks.is_mod_or_superior(self.context)
        is_owner = await self.context.bot.is_owner(self.context.author)
        is_guild_owner = (
            self.context.author == self.context.guild.owner if self.context.guild else is_owner
        )
        before = [
            x
            for x in [
                getattr(cog, "_{0.__class__.__name__}__red_permissions_before".format(cog), None)
                for cog in self.context.bot.cogs.values()
            ]
            if x
        ]
        after = [
            x
            for x in [
                getattr(cog, "_{0.__class__.__name__}__red_permissions_after".format(cog), None)
                for cog in self.context.bot.cogs.values()
            ]
            if x
        ]

        # reused func from d.py's HelpFormatter
        def sane_no_suspension_point_predicate(tup):
            cmd = tup[1]
            if self.is_cog():
                # filter commands that don't exist to this cog.
                if cmd.instance is not self.command:
                    return False

            if cmd.hidden and not self.show_hidden:
                return False

            return True

        # handle the permission aspect of `checks.mod_or_permissions()` (etc)
        async def process_closure(check_obj) -> bool:
            """
            Takes a check object, returns the permission resolution section of it
            """
            to_check = {}
            if not hasattr(check_obj, "__closure__"):
                return False
            for cell_object in check_obj.__closure__:
                to_check.update(cell_object.cell_contents)
            return await checks.check_permissions(self.context, to_check)

        async def special_check_handling(com) -> bool:
            """
            This exists to expedite handling of permissions cog interactions
            """
            level = "all"
            lcheck = filter(lambda x: x.__module__ == "redbot.core.checks", com.checks)
            for check in lcheck:
                if any(x in str(check) for x in ("admin", "mod", "guildowner")):
                    level = "guildowner"
                elif "owner" in str(check):
                    level = "owner"
                    break
            skip_perm_model = False
            for check in before:
                if check is None:
                    continue
                try:
                    if asyncio.iscoroutinefunction(check):
                        override = await check(self.context, level=level)
                    else:
                        override = check(self.context, level=level)
                except:
                    override = None
                if override is False:
                    return override
                if override is True:
                    skip_perm_model = True

            if com in permissions_dict["denied"] and not skip_perm_model:
                return False
            # default to True because this can interact with checks without perm reqs
            has_role_or_perms = True  # for storing for conjunction with after checks
            for check in com.checks:
                if check.__module__ == "redbot.core.checks" and any(
                    x in str(check) for x in ("owner", "admin", "mod")
                ):
                    if skip_perm_model:
                        continue
                    if com in permissions_dict["allowed"]:
                        skip_perm_model = True
                        continue
                    if "guildowner" in str(check):
                        if is_guild_owner:
                            continue
                    elif "owner" in str(check):
                        if is_owner:
                            continue
                    elif "admin" in str(check):
                        if is_admin:
                            continue
                    elif "mod" in str(check):
                        if is_mod:
                            continue
                    elif await process_closure(check):
                        continue
                    else:
                        has_role_or_perms = False
                else:  # Still need to process other checks too
                    ret = await discord.utils.maybe_coroutine(check, self.context)
                    if not ret:
                        return False
            else:
                if not skip_perm_model:
                    for check in after:
                        if check is None:
                            continue
                        try:
                            if asyncio.iscoroutinefunction(check):
                                override = await check(self.context, level=level)
                            else:
                                override = check(self.context, level=level)
                        except:
                            override = None
                        if override is False:
                            return False
                        if override is None and not has_role_or_perms:
                            return False

            # Stuff below here in this funtion is mostly taken from
            # discord.py with minor tweaks to use the above
            # https://github.com/Rapptz/discord.py
            # local checks
            cog = com.instance
            if cog is not None:
                try:
                    local_check = getattr(cog, "_{0.__class__.__name__}__local_check".format(cog))
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
                return await special_check_handling(com)
            except CommandError:
                return False

        iterator = (
            self.command.all_commands.items()
            if not self.is_cog()
            else self.context.bot.all_commands.items()
        )
        if self.show_check_failure:
            return filter(sane_no_suspension_point_predicate, iterator)

        # Gotta run every check and verify it
        ret = []
        for elem in iterator:
            valid = await predicate(elem)
            if valid:
                ret.append(elem)
        return ret
