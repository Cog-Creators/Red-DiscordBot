.. V3 Mod log

.. role:: python(code)
    :language: python


=======
Mod log
=======

Mod log has now been separated from Mod for V3.

***********
Basic Usage
***********

.. code-block:: python

    from redbot.core import modlog
    import discord

    class MyCog:
        @commands.command()
        @checks.admin_or_permissions(ban_members=True)
        async def ban(self, ctx, user: discord.Member, reason: str = None):
            await ctx.guild.ban(user)
            case = await modlog.create_case(
                ctx.guild, ctx.message.created_at, "ban", user,
                ctx.author, reason, until=None, channel=None
            )
            await ctx.send("Done. It was about time.")


**********************
Registering Case types
**********************

To register a single case type:

.. code-block:: python

    from redbot.core import modlog
    import discord

    class MyCog:
        def __init__(self, bot):
            self.register_task = bot.loop.create_task(self.register_case())

        def cog_unload(self):
            self.register_task.cancel()

        @staticmethod
        async def register_case():
            ban_case = {
                "name": "ban",
                "default_setting": True,
                "image": ":hammer:",
                "case_str": "Ban",
                "audit_type": "ban"
            }
            try:
                await modlog.register_casetype(**ban_case)
            except RuntimeError:
                pass

To register multiple case types:

.. code-block:: python

    from redbot.core import modlog
    import discord

    class MyCog:
        def __init__(self, bot):
            self.register_task = bot.loop.create_task(self.register_cases())

        def cog_unload(self):
            self.register_task.cancel()

        @staticmethod
        async def register_cases():
            new_types = [
                {
                    "name": "ban",
                    "default_setting": True,
                    "image": ":hammer:",
                    "case_str": "Ban",
                    "audit_type": "ban"
                },
                {
                    "name": "kick",
                    "default_setting": True,
                    "image": ":boot:",
                    "case_str": "Kick",
                    "audit_type": "kick"
                }
            ]
            try:
                await modlog.register_casetypes(new_types)
            except RuntimeError:
                pass

.. important::
    Image should be the emoji you want to represent your case type with.


*************
API Reference
*************

Mod log
=======

.. automodule:: redbot.core.modlog
    :members:
