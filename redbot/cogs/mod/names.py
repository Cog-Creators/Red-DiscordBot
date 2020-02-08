from datetime import datetime
from typing import cast

import discord
from redbot.core import commands, i18n, checks
from redbot.core.utils.common_filters import (
    filter_invites,
    filter_various_mentions,
    escape_spoilers_and_mass_mentions,
)
from redbot.core.utils.mod import get_audit_reason
from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)


class ModInfo(MixinMeta):
    """
    Commands regarding names, userinfo, etc.
    """

    async def get_names_and_nicks(self, user):
        names = await self.settings.user(user).past_names()
        nicks = await self.settings.member(user).past_nicks()
        if names:
            names = [escape_spoilers_and_mass_mentions(name) for name in names if name]
        if nicks:
            nicks = [escape_spoilers_and_mass_mentions(nick) for nick in nicks if nick]
        return names, nicks

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_nicknames=True)
    @checks.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx: commands.Context, user: discord.Member, *, nickname: str = ""):
        """Change a user's nickname.

        Leaving the nickname empty will remove it.
        """
        nickname = nickname.strip()
        me = cast(discord.Member, ctx.me)
        if not nickname:
            nickname = None
        elif not 2 <= len(nickname) <= 32:
            await ctx.send(_("Nicknames must be between 2 and 32 characters long."))
            return
        if not (
            (me.guild_permissions.manage_nicknames or me.guild_permissions.administrator)
            and me.top_role > user.top_role
            and user != ctx.guild.owner
        ):
            await ctx.send(
                _(
                    "I do not have permission to rename that member. They may be higher than or "
                    "equal to me in the role hierarchy."
                )
            )
        else:
            try:
                await user.edit(reason=get_audit_reason(ctx.author, None), nick=nickname)
            except discord.Forbidden:
                # Just in case we missed something in the permissions check above
                await ctx.send(_("I do not have permission to rename that member."))
            except discord.HTTPException as exc:
                if exc.status == 400:  # BAD REQUEST
                    await ctx.send(_("That nickname is invalid."))
                else:
                    await ctx.send(_("An unexpected error has occured."))
            else:
                await ctx.send(_("Done."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx, *, user: discord.Member = None):
        """Show information about a user.

        This includes fields for status, discord join date, server
        join date, voice state and previous names/nicknames.

        If the user has no roles, previous names or previous nicknames,
        these fields will be omitted.
        """
        author = ctx.author
        guild = ctx.guild

        if not user:
            user = author

        #  A special case for a special someone :^)
        special_date = datetime(2016, 1, 10, 6, 8, 4, 443000)
        is_special = user.id == 96130341705637888 and guild.id == 133049272517001216

        roles = user.roles[-1:0:-1]
        names, nicks = await self.get_names_and_nicks(user)

        joined_at = user.joined_at if not is_special else special_date
        since_created = (ctx.message.created_at - user.created_at).days
        if joined_at is not None:
            since_joined = (ctx.message.created_at - joined_at).days
            user_joined = joined_at.strftime("%d %b %Y %H:%M")
        else:
            since_joined = "?"
            user_joined = _("Unknown")
        user_created = user.created_at.strftime("%d %b %Y %H:%M")
        voice_state = user.voice
        member_number = (
            sorted(guild.members, key=lambda m: m.joined_at or ctx.message.created_at).index(user)
            + 1
        )

        created_on = _("{}\n({} days ago)").format(user_created, since_created)
        joined_on = _("{}\n({} days ago)").format(user_joined, since_joined)

        activity = _("Chilling in {} status").format(user.status)
        if user.activity is None:  # Default status
            pass
        elif user.activity.type == discord.ActivityType.playing:
            activity = _("Playing {}").format(user.activity.name)
        elif user.activity.type == discord.ActivityType.streaming:
            activity = _("Streaming [{}]({})").format(user.activity.name, user.activity.url)
        elif user.activity.type == discord.ActivityType.listening:
            activity = _("Listening to {}").format(user.activity.name)
        elif user.activity.type == discord.ActivityType.watching:
            activity = _("Watching {}").format(user.activity.name)

        if roles:

            role_str = ", ".join([x.mention for x in roles])
            # 400 BAD REQUEST (error code: 50035): Invalid Form Body
            # In embed.fields.2.value: Must be 1024 or fewer in length.
            if len(role_str) > 1024:
                # Alternative string building time.
                # This is not the most optimal, but if you're hitting this, you are losing more time
                # to every single check running on users than the occasional user info invoke
                # We don't start by building this way, since the number of times we hit this should be
                # infintesimally small compared to when we don't across all uses of Red.
                continuation_string = _(
                    "and {numeric_number} more roles not displayed due to embed limits."
                )
                available_length = 1024 - len(continuation_string)  # do not attempt to tweak, i18n

                role_chunks = []
                remaining_roles = 0

                for r in roles:
                    chunk = f"{r.mention}, "
                    chunk_size = len(chunk)

                    if chunk_size < available_length:
                        available_length -= chunk_size
                        role_chunks.append(chunk)
                    else:
                        remaining_roles += 1

                role_chunks.append(continuation_string.format(numeric_number=remaining_roles))

                role_str = "".join(role_chunks)

        else:
            role_str = None

        data = discord.Embed(description=activity, colour=user.colour)
        data.add_field(name=_("Joined Discord on"), value=created_on)
        data.add_field(name=_("Joined this server on"), value=joined_on)
        if role_str is not None:
            data.add_field(name=_("Roles"), value=role_str, inline=False)
        if names:
            # May need sanitizing later, but mentions do not ping in embeds currently
            val = filter_invites(", ".join(names))
            data.add_field(name=_("Previous Names"), value=val, inline=False)
        if nicks:
            # May need sanitizing later, but mentions do not ping in embeds currently
            val = filter_invites(", ".join(nicks))
            data.add_field(name=_("Previous Nicknames"), value=val, inline=False)
        if voice_state and voice_state.channel:
            data.add_field(
                name=_("Current voice channel"),
                value="{0.mention} ID: {0.id}".format(voice_state.channel),
                inline=False,
            )
        data.set_footer(text=_("Member #{} | User ID: {}").format(member_number, user.id))

        name = str(user)
        name = " ~ ".join((name, user.nick)) if user.nick else name
        name = filter_invites(name)

        if user.avatar:
            avatar = user.avatar_url_as(static_format="png")
            data.set_author(name=name, url=avatar)
            data.set_thumbnail(url=avatar)
        else:
            data.set_author(name=name)

        await ctx.send(embed=data)

    @commands.command()
    async def names(self, ctx: commands.Context, *, user: discord.Member):
        """Show previous names and nicknames of a user."""
        names, nicks = await self.get_names_and_nicks(user)
        msg = ""
        if names:
            msg += _("**Past 20 names**:")
            msg += "\n"
            msg += ", ".join(names)
        if nicks:
            if msg:
                msg += "\n\n"
            msg += _("**Past 20 nicknames**:")
            msg += "\n"
            msg += ", ".join(nicks)
        if msg:
            msg = filter_various_mentions(msg)
            await ctx.send(msg)
        else:
            await ctx.send(_("That user doesn't have any recorded name or nickname change."))
