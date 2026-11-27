======================
Creating a bot account
======================

To use Red you will require a bot account and to enable privileged intents. Both these steps will be covered below.

.. _creating-a-bot-account:

----------------------------
Creating the bot application
----------------------------

In order to use Red, we must first create a Discord Bot account.

Creating a Bot account is a pretty straightforward process.

1. Make sure you're logged on to the `Discord website <https://discord.com>`_.
2. Navigate to the `application page <https://discord.com/developers/applications>`_
3. Click on the "New Application" button.

    .. image:: /.resources/bot-guide/discord_create_app_button.png
        :alt: The new application button.

4. Give the application a name, check the box to accept the Terms of Service, and click "Create".

    .. image::  /.resources/bot-guide/discord_create_app_form.png
        :alt: The new application form filled in.

5. Open the "Overview" category and navigate to the "Installation" tab on the left side of the screen.

    .. image:: /.resources/bot-guide/discord_installation_tab.png
        :alt: The installation tab in the application page.

6. Uncheck "User Install" and set "Install Link" to "None"

    .. image:: /.resources/bot-guide/discord_installation_options.png
        :alt: How the Installation options should look like for most people.

7. Navigate to the "Bot" tab on the left side of the screen.

    .. image:: /.resources/bot-guide/discord_bot_tab.png
        :alt: The bot tab in the application page.

8. If you want others to be able to invite your bot tick the **Public Bot**. Keeping it unticked will prevent others from inviting your bot to their servers and only you will be able to add the bot to servers (provided that you have needed permissions in the server you want to add the bot to).

    - Make sure **Require OAuth2 Code Grant** is unchecked.

    .. image::  /.resources/bot-guide/discord_bot_user_options.png
        :alt: How the Bot User options should look like for most people.

9. Acquire the token using the "Reset Token" button, then "Copy" after it is revealed.

    .. warning::

        Do not share your token as it is like your password.
        If you shared your token you can regenerate it.

Continue to the next section to enable privileged intents.

.. _enabling-privileged-intents:

---------------------------
Enabling Privileged Intents
---------------------------
.. warning::
    In its default (highly recommended) configuration, Red requires enabling
    the Guild (Server) Members Intent and Message Content Intent.
    You can read more about this in the :doc:`intents` document.

1. Make sure you're logged on to the `Discord website <https://discord.com>`_.
2. Navigate to the `application page <https://discord.com/developers/applications>`_
3. Click on the bot you want to enable privileged intents for.
4. Navigate to the bot tab on the left side of the screen.

    .. image:: /.resources/bot-guide/discord_bot_tab.png
        :alt: The bot tab in the application overview page.

5. Scroll down to the "Privileged Gateway Intents" section, enable the Server Members Intent and Message Content Intent, then save your changes.

    .. image:: /.resources/bot-guide/discord_privileged_intents.png
        :alt: The privileged gateway intents selector.

.. warning::

    If your bot is accessible to 10,000 or more users across all the servers it's in,
    Discord will ask you to submit a request for review of your bot's use of the Privileged Intents.
    This usually happens within 24 hours of your bot reaching the 10,000-user threshold.

    We explain what Privileged Intents are and how to apply for them in the :doc:`intents` document.

*Parts of this guide have been adapted from* `discord.py intro <https://discordpy.readthedocs.io/en/stable/discord.html#discord-intro>`_ *and* `discord.py privileged intents <https://discordpy.readthedocs.io/en/stable/intents.html#privileged-intents>`_.
