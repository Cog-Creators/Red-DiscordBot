.. v3.1.0 Changelog

================
v3.1.0 Changelog
================

-----
Audio
-----

------
Config
------

 * Updated Mongo driver to support large guilds (`#2536`_)
 * Introduced ``init_custom`` method on Config objects (`#2545`_)
 * We now record custom group primary key lengths in the core config object (`#2550`_)
 * Migrated internal UUIDs to maintain cross platform consistency (`#2604`_)

----------
discord.py
----------

-------------
Setup Scripts
-------------

 * ``redbot-setup`` now uses the click CLI library (`#2579`_)
 * ``redbot-setup convert`` now used to convert between libraries (`#2579`_)
 * Backup support for Mongo is currently broken (`#2579`_)

.. _#2536 link: https://github.com/Cog-Creators/Red-DiscordBot/pull/2536
.. _#2545 link: https://github.com/Cog-Creators/Red-DiscordBot/pull/2545
.. _#2550 link: https://github.com/Cog-Creators/Red-DiscordBot/pull/2550
.. _#2579 link: https://github.com/Cog-Creators/Red-DiscordBot/pull/2579
.. _#2604 link: https://github.com/Cog-Creators/Red-DiscordBot/pull/2604
