------------------
Installing the bot
------------------

To install without audio:

:code:`pip3 install -U --process-dependency-links red-discordbot --user`

To install with audio:

:code:`pip3 install -U --process-dependency-links red-discordbot[voice] --user`

To install the development version (without audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot --user`

To install the development version (with audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot[voice] --user`

.. tip:: If after the pip installation the :code:`redbot`, :code:`redbot-setup` and :code:`redbot-launcher` commands don't work, you need to add the :code:`~/.local/bin` folder to your PATH.

   :code:`nano ~/.bash_profile`

   Add the following line to the end of the file:

   :code:`PATH=$PATH:~/.local/bin`

   Save and exit :code:`ctrl + O; enter; ctrl + x`

.. include:: red_setup.rst

.. include:: red_run.rst