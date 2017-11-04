.. image:: https://readthedocs.org/projects/red-discordbot/badge/?version=v3-develop
    :target: http://red-discordbot.readthedocs.io/en/v3-develop/?badge=v3-develop
    :alt: Documentation Status

.. image:: https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square
    :target: http://makeapullrequest.com
    :alt: PRs Welcome

.. image:: https://d322cqt584bo4o.cloudfront.net/red-discordbot/localized.svg
    :target: https://crowdin.com/project/red-discordbot
    :alt: Crowdin

********************
Red - Discord Bot v3
********************

**This is alpha and very much a work in progress. Regular use is not recommended.
There will not be any effort not to break current installations.**

How to install
^^^^^^^^^^^^^^

Using python3 pip::

    pip install --process-dependency-links -U git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop
    redbot-setup
    redbot <name>

To install requirements for voice::

    pip install --process-dependency-links -U git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot[voice]

To install all requirements for docs and tests::

    pip install --process-dependency-links -U git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot[test,docs]
