.. Permissions Cog Reference

=========================
Permissions Cog Reference
=========================

------------
How it works
------------

When loaded, the permissions cog will allow you
to define extra custom rules for who can use a command

If no applicable rules are found, the command will behave as if
the cog was not loaded.

-------------
Rule priority
-------------

Rules set will be checked in the following order


    1. Owner level command specific settings
    2. Owner level cog specific settings
    3. Server level command specific settings
    4. Server level cog specific settings

For each of those, settings have varying priorities (listed below, highest to lowest priority)

    1. User whitelist
    2. User blacklist
    3. Voice Channel whitelist
    4. Voice Channel blacklist
    5. Text Channel whitelist
    6. Text Channel blacklist
    7. Role settings (see below)
    8. Server whitelist
    9. Server blacklist

For the role whitelist and blacklist settings,
roles will be checked individually in order from highest to lowest role the user has
Each role will be checked for whitelist, then blacklist. The first role with a setting
found will be the one used.

