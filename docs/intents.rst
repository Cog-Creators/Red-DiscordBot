.. _intents:
.. |br| raw:: html

   <br />

==========================================
About (privileged) intents and public bots
==========================================

This page aims to explain Red's current intents requirements,
our stance regarding "public bots", and the discord bot verification process.

To clarify:

- **Small bots** are bots under 100 servers. They currently do not need to undergo Discord's
  bot verification process
- **Public bots** (or big bots) are bots that have reached 100 servers. They need to be
  `verified <https://support-dev.discord.com/hc/en-us/articles/23926564536471-How-Do-I-Get-My-App-Verified>`_
  by Discord to join more than 100 servers and gain privileged intents

.. warning::

  It is **very** important that you fully read this page if you're the owner of a public bot or strive to scale your bot at that level.

.. _intents-public-bots:

-----------
Public bots
-----------

Public bots, or big bots, are not our target audience and we **do not** offer support for them.

Red was designed with one single goal in mind: a bot that you can host on your own hardware
and customize to your needs, making it really *your* bot. **The target audience of Red are server
owners with a few servers**, often with specific needs that can be covered by the vast cog ecosystem
that the community has built over the years. |br| Red was never built with big bots in mind,
bots with thousands upon thousands of servers: these bots face unique challenges. Large bots need
to be extremely efficient to handle the large amount of requests they receive, and often need to
distribute this work across multiple processes or machines to keep up.
Such Red instances *do exist*, and it is not impossible to adapt Red and meet those criteria,
but it requires work and bot owners with the technical knowledge to make it happen.
It is **not** something that we support. |br|
When your bot reaches the public bot scale and it is therefore required to be verified it
is *expected* that you know what's in your bot and how it works: that doesn't just mean on the
surface level, it means coding knowledge and the ability to maintain it on your own.

.. _intents-bot-verification-process:

------------------------
Bot verification process
------------------------

When your bot ceases to be a small bot Discord will require you to verify your bot before allowing
it to join more servers and gain privileged intents. If you've read the previous section,
you will know that we do **not** support public bots. Logically, we also do not provide help for
the verification process.

Regardless of our stance, we do feel the need to give some pointers: many bot owners reach this point
and become fairly lost, as they've simply been *users* so far.
They have installed their bot, some cogs, personalized it, but have not needed to write any code.
Unless they also have an interest in development, they will likely not have a clue about
what's going under the hood, much like you're not expected to be a mechanic to drive your car. And there's
nothing wrong with that! Red has been designed to be as user friendly as possible. |br|
The problem is this: Red is an outlier. Discord has built the bot verification process with the expectation
that the owner knows *on a technical level* what their bot does and how it works. And this is because outside
Red, the typical bot owner is also a developer who coded their own bot from scratch.

While, again, we *cannot* support you going forward we want to give you some pointers to follow when filling
out your application:

- Learn on a technical level what intents are and what's going on, under the hood, in your bot. Knowing its
  features at a surface level is not enough. What features need intents to work and why?
- Forget that you're hosting Red. You're hosting *a bot* and Discord wants to know what *your bot* does and why
  you're requesting privileged intents. |br| A **very bad** answer is: *"Because Red needs them"*. |br|
  A **good** answer is: *"My bot has X features and it needs Y intents to work properly"*. |br| We've had a fair share
  of people that in their naivety went with the bad answer and it seems that at this point merely mentioning Red
  is a guaranteed way to have your application rejected.

.. _intents-intents:

-------
Intents
-------

Red expects **all intents** to be active. It is possible, but not recommended, to disable
specific intents using the ``--disable-intent`` flag. If an intent is missing, you may
experience errors due to Red expecting information provided by the intent to be present.

Discord currently considers 3 intents to be
`privileged <https://support-dev.discord.com/hc/en-us/articles/6205754771351-How-do-I-get-Privileged-Intents-for-my-bot>`_,
and requires large bots to additionally apply for access to these intents. **If you have a small
bot**, you can simply follow :ref:`these instructions <enabling-privileged-intents>` to enable them.

A breakdown of how privileged intents are used in Red is provided below.

The **Message Content** intent is required to use text based commands and inputs for
configuration and all built in functionality. App commands (also known as slash commands)
are limited to a total of 100 top level commands, which is difficult to manage on
a modular bot. The approach we have taken to address this issue is to allow 3rd party
cogs to provide slash commands, but require bot owners to pick which slash commands
they actually want to use with the ``[p]slash`` command.
Under this system, bot management commands that are not exposed to users are still
expected to be provided as text commands, which requires the bot to be able to access
message content. There are no current plans to provide slash versions of core commands.

.. note::
  It is possible to work around this intent by using the ``--mentionable``
  flag, and using the bot mention as a prefix to use text based commands.

The **Guild Members** intent is required to properly cache member information, including
what users are in each server, what roles they have, what their name is, etc. It is also
required to receive events corresponding to when members join or leave a server, and when
they change their nickname or other server options. Almost all cogs expect to be able
to reference the member cache in order to avoid making API requests, and are not set
up to check if the intent is present before doing so.

The **Guild Presences** intent is required to view the activities and status of
users. Cogs which perform actions on users based on their activity or status will
be unable to access this information if this intent is not enabled.
