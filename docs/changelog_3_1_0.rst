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

 * Updated Mongo driver to support large guilds
 * Introduced ``init_custom`` method on Config objects
 * We now record custom group primary key lengths in the core config object
 * Migrated internal UUIDs to maintain cross platform consistency

----------
discord.py
----------

-------------
Setup Scripts
-------------

 * ``redbot-setup`` now uses the click CLI library
 * ``redbot-setup convert`` now used to convert between libraries
 * Backup support for Mongo is currently broken
