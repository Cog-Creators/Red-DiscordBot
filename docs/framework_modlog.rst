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

    from core import modlog
    import discord

    class MyCog:
        @commands.command()
        @checks.admin_or_permissions(ban_members=True)
        async def ban(self, ctx, user: discord.Member, reason: str=None):
            await ctx.guild.ban(user)
            case = modlog.create_case(
                ctx.guild, ctx.message.created_at, "Ban", user,
                ctx.author, reason, until=None, channel=None
            )
            await ctx.send("Done. It was about time.")


**********************
Registering Case types
**********************

To register a single case type:

.. code-block:: python

    from core import modlog
    import discord

    class MyCog:
        def __init__(self, bot):
            ban_case = {
                "name": "Ban",
                "default_setting": True,
                "image": "https://twemoji.maxcdn.com/2/72x72/1f528.png"
            }
            modlog.register_casetype(ban_case)

To register multiple case types:

.. code-block:: python

    from core import modlog
    import discord

    class MyCog:
        def __init__(self, bot):
            new_types = [
                {
                    "name": "Ban",
                    "default_setting": True,
                    "image": "https://twemoji.maxcdn.com/2/72x72/1f528.png"
                },
                {
                    "name": "Kick",
                    "default_setting": True,
                    "image": "https://twemoji.maxcdn.com/2/72x72/1f462.png"
                }
            ]
            modlog.register_casetypes(new_types)

.. important::
    To find an image for your case type, look through
    http://twitter.github.io/twemoji/2/test/preview.html


*************
API Reference
*************

Mod log
=========

.. automodule:: core.modlog
    :members:
    :special-members: __str__
