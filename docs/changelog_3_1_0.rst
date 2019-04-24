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

---
Mod
---

 * Admins can now decide how many times message has to be repeated before ``deleterepeats`` removes it (`#2437`_)

-------------
Setup Scripts
-------------

 * ``redbot-setup`` now uses the click CLI library (`#2579`_)
 * ``redbot-setup convert`` now used to convert between libraries (`#2579`_)
 * Backup support for Mongo is currently broken (`#2579`_)

.. _#2437: https://github.com/Cog-Creators/Red-DiscordBot/pull/2437
.. _#2536: https://github.com/Cog-Creators/Red-DiscordBot/pull/2536
.. _#2545: https://github.com/Cog-Creators/Red-DiscordBot/pull/2545
.. _#2550: https://github.com/Cog-Creators/Red-DiscordBot/pull/2550
.. _#2579: https://github.com/Cog-Creators/Red-DiscordBot/pull/2579
.. _#2604: https://github.com/Cog-Creators/Red-DiscordBot/pull/2604
