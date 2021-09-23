.. _intents:
.. |br| raw:: html

   <br />

==========================================
About (privileged) intents and public bots
==========================================

This page aims to explain Red's current intents requirements,
our stance regarding "public bots" and the impact of some announced
Discord changes coming in April 2022.

To clarify:

- **Small bots** are bots under 100 servers. They currently do not need to undergo Discord's
  bot verification process
- **Public bots** (or big bots) are bots that have reached 100 servers. They need to be
  `verified <https://support.discord.com/hc/en-us/articles/360040720412-Bot-Verification-and-Data-Whitelisting>`_
  by Discord to join more than 100 servers and gain privileged intents

.. warning::

  It is **very** important that you fully read this page if you're the owner of a public bot or strive to scale your bot at that level.

.. _intents-intents:

-------
Intents
-------

Red currently requires **all intents** to be active in order to function properly.

The reason for this requirement is that there are some technical challenges that need
to be overcome before we're able to adapt Red to function with only *some* intents:
these challenges are mainly due to the modular / extensible nature of Red and the fact
that Red has a long history (dating back to 2016!), making big changes naturally slower
to happen. In comparison, intents have been introduced fairly recently. |br|
This is not a problem if you have a small bot: you can simply go to the
`Discord development portal <https://discord.com/developers/applications/me>`_
and enable them. However, if you have a public bot Discord will want you to attain
verified status: you should read :ref:`our stance regarding public bots <intents-public-bots>`
and our guidelines for the :ref:`verification process <intents-bot-verification-process>`.

.. _intents-public-bots:

-----------
Public bots
-----------

Public bots, or big bots, are not our target audience and we **do not** offer support for them.

Red was designed with one single goal in mind: a bot that you can host on your own hardware
and customize to your needs, making it really *your* bot. **The target audience of Red are server
owners with a few servers**, often with specific needs that can be covered by the vast cog ecosystem
that the community has built over the years. |br| Red was never built with big bots in mind,
bots with thousands upon thousands of servers: these bots face unique challenges.
Such Red instances *do exist*, it is not impossible to adapt Red and meet those criteria,
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
They have installed their bot, some cogs, personalized it, yadda yadda. Again, they have been users,
not developers. Unless they also have an interest in development, they will likely not have a clue about
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

.. _intents-slash-commands:

---------------------------------
Message intent and slash commands
---------------------------------

.. warning::

  If you own a public bot it is extremely important that you read this section.

Discord has announced that **starting April 2022** the content of users' messages
`will be "locked" behind message intent <https://support-dev.discord.com/hc/en-us/articles/4404772028055>`_ |br|
If you're the owner of a small bot, fear not, this is yet another box that you have to tick from the
`Discord development portal <https://discord.com/developers/applications/me>`_. |br|
But if you're the owner of a public bot, things might be a lot less pleasant.

To recap, unless you have
message intent, you will only receive message content for:

- Messages that your bot sends
- Messages that your bot receives in DM
- Messages in which your bot is mentioned

In case it's not clear by now, your bot needs message content to parse (see) the commands it receives. And if
you don't attain message intent, your bot will not be able to... well, do anything. |br|
The *bandaid fix* is for you to change your bot's prefix to a mention and a good portion of your commands will likely
still work. You will however lose many functions, namely anything that relies on seeing message content to act. |br|
The more *proper fix* is also not easy. You will need to justify your need for the message intent to Discord and
they will only accept "compelling use cases".
`It is not known what those even entail <https://gist.github.com/spiralw/091714718718379b6efcdbcaf807a024#q-what-usecases-will-be-valid>`_ at this point, but they have already stated that "parsing commands" is not a valid justification. |br|
To make the matter worse, Discord is making `a huge push for all bot developers to implement slash commands <https://support.discord.com/hc/en-us/articles/1500000368501-Slash-Commands-FAQ>`_, which at the moment
are rather lacking in features and cannot cover all the functionalities that standard commands offer. |br|
Discord staff
`stated that they will want your bot to have slash commands when you ask for message intent <https://gist.github.com/spiralw/091714718718379b6efcdbcaf807a024#q-if-we-are-granted-this-intent-will-bots-be-sanctioned-if-they-use-it-for-their-own-use-case-but-also-to-continue-to-run-normal-non-slash-commands-or-do-we-assume-that-if-you-are-granted-the-intent-you-are-trusted-with-it-and-are-allowed-to-use-it-for-additional-uses>`_. |br|
Slash commands might very well turn out to be a big undertaking for the Red team to implement, even more now that our
underlying library, `discord.py <https://github.com/Rapptz/discord.py>`_, has been discontinued. |br|
The time window that Discord is giving us to adapt is very narrow: **Red will likely not be able to support slash
commands for April 2022** and you should plan accordingly.