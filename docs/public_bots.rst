.. _public-bots:

=======================
About public (big) bots
=======================

This page aims to explain our stance regarding "public bots" and the Discord app verification process.

To clarify:

- **Small bots** are bots under 100 servers. They currently do not need to undergo Discord's
  app verification process
- **Public bots** (or big bots) are bots that have reached 100 servers. They need to be
  `verified <https://support-dev.discord.com/hc/en-us/articles/23926564536471-How-Do-I-Get-My-App-Verified>`_
  by Discord to join more than 100 servers

.. warning::

  It is **very** important that you fully read this page if you're the owner of a public bot or strive to scale your bot at that level.

.. _public-bots-public-bots:

-----------
Public bots
-----------

Public bots, or big bots, are not our target audience and we **do not** offer support for them.

| Red was designed with one single goal in mind: a bot that you can host on your own hardware
  and customize to your needs, making it really *your* bot.
  **The target audience of Red are server owners with a few servers**, often with specific needs
  that can be covered by the vast cog ecosystem that the community has built over the years.
| Red was never built with big bots in mind, bots with thousands upon thousands of servers:
  these bots face unique challenges. Large bots need to be extremely efficient to handle
  the large amount of requests they receive, and often need to distribute this work across multiple
  processes or machines to keep up.
  Such Red instances *do exist*, and it is not impossible to adapt Red and meet those criteria,
  but it requires work and bot owners with the technical knowledge to make it happen.
  It is **not** something that we support.
| When your bot reaches the public bot scale and it is therefore required to be verified it
  is *expected* that you know what's in your bot and how it works: that doesn't just mean on the
  surface level, it means coding knowledge and the ability to maintain it on your own.

.. _public-bots-app-verification-process:

------------------------
App verification process
------------------------

When your bot ceases to be a small bot Discord will require you to verify your bot application
before allowing it to join more servers. If you've read the previous section, you will know
that we do **not** support public bots. Logically, we also do not provide help for
the verification process.

| Regardless of our stance, we do feel the need to give some pointers: many bot owners reach
  this point and become fairly lost, as they've simply been *users* so far.
  They have installed their bot, some cogs, personalized it, but have not needed to write any code.
  Unless they also have an interest in development, they will likely not have a clue about
  what's going under the hood, much like you're not expected to be a mechanic to drive your car.
  And there's nothing wrong with that! Red has been designed to be as user friendly as possible.
| The problem is this: Red is an outlier. Discord expects that the owner knows
  *on a technical level* what their bot does and how it works. And this is because outside Red,
  the typical bot owner is also a developer who coded their own bot from scratch.

While, again, we *cannot* support you going forward we want to give you some pointers to follow
when filling out your application:

- Learn on a technical level what's going on, under the hood, in your bot.
  Knowing its features at a surface level is not enough.
  How are those features implemented in code, what API features do they use (especially ones
  that require privileged intents) and why?
- Forget that you're hosting Red. You're hosting *a bot* and Discord wants you to know
  what *your bot* does, what (user) data it processes, and why.
  **You are the one responsible** for what your bot does and the data it collects and need to
  ensure *yourself* that you're compliant with Discord Developer Policy,
  Discord Developer Terms of Service, and any applicable laws.
