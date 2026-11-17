.. _privileged-intents:

========================
About privileged intents
========================

.. warning::

    It is **very** important that you fully read this page before applying for Privileged Intents.

    If you plan on (or already are) using Red for hosting a public bot
    (a bot that can be invited by any user), you should read `public-bots` as well.

| If your bot is accessible to 10,000 or more users across all the servers it's in,
  Discord will ask you to submit a request for review of your bot's use of the Privileged Intents.
| **If your bot does not have that many users**, you can simply follow :ref:`these instructions <enabling-privileged-intents>`
  to enable them.

If your bot ever reaches the 10,000-user threshold, you will receive an official message from Discord
in a direct message (DM) on Discord *and* in an e-mail message sent to the user that owns the bot application.
This should generally happen within 24 hours of your bot reaching this threshold.

| In its default (highly recommended) configuration, Red requires enabling the *Guild (Server) Members Intent*
  and *Message Content Intent*.
| *Guild Members Intent* is especially important as a large number of cogs,
  both 1st-party and 3rd-party are not prepared to work without it, even in cases where they theoretically could.
  Such cogs may either not work as expected or completely error out.
| User experience without the *Message Content Intent* is also considerably worse as it prevents use of
  bot's text-based commands using bot's prefix outside DMs. Instead, users have to use the bot mention as the prefix
  to use the text-based commands. It's worth noting that Discord does not consider **this specific use case**
  to be valid during Privileged Intents review and you **should avoid** using it as justification anywhere
  in your request.
| For both of these Privileged Intents, there are a lot of use cases that Discord will consider valid,
  including some in core cogs. The use cases from core cogs can be found in the sample answers
  listed in the `intents-how-to` section.

.. _intents-privacy-policy:

What about the privacy policy?
------------------------------

If you've already looked at the form for requesting Privileged Intents already,
you might have noticed that it asks for a privacy policy.
Per `Discord Developer Terms of Service <https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service>`__,
Discord requires that you:

    provide and adhere to a privacy policy for your Application that is compliant with
    applicable privacy laws and clearly, accurately, and fully describes to users of
    your Application what data you collect, how you use and share such data with us
    and third parties, and how users can request deletion of such data.

While we do provide some guidance and samples, you should keep in mind that in the end,
**you are the one responsible** for the privacy policy you've published and need to ensure
*yourself* that you're compliant with Discord Developer Terms of Service and any applicable laws.

The privacy policy needs to be hosted somewhere on the Internet. To make it easy for you,
we provide a simple GitHub repository template that you can use to generate a repository
that GitHub can turn into a live website for you with no separate hosting necessary.

The repository also comes with a sample privacy policy in the ``index.md`` file which describes data
collected by Red's core cogs and can be used as a starting point for your own instance.
This file is hosted as the main page on the generated GitHub Pages website.

The sample privacy policy also links to the ``3rd-party.html`` file for information about data
that's collected in addition to what's described in the main document. You can generate
the ``3rd-party.html`` file for your own bot by running its ``[p]mydata 3rdparty`` command
and uploading its result to the repository you created.

.. _intents-privacy-policy-template:

How to use the privacy policy repository template?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#.  Login to your GitHub account or register, if you don't have one already.
#.  Go to https://github.com/Cog-Creators/Red-Privacy-Policy/generate.
#.  Set a name for the repository. This name should probably contain something identifying
    the specific bot that this policy will apply to as a single repository created from
    this template can only represent one bot.
#.  Keep visibility set to "Public".
#.  Click on "Create repository".
#.  After the repository is created, you'll be presented with the repository page.
    Wait about 20 seconds, then refresh the page. You should now see a new README page.
#.  Continue by following the step-by-step instructions in the new repository's README.

.. _intents-how-to:

How to apply for Privileged Intents?
------------------------------------

#.  Go to the `Discord Developer Portal <https://discord.com/developers/applications>`__.
    You should see a notification about required Privileged Intents approval at the top:

    .. image:: /.resources/intents/action_required_app_list.png
        :alt: The "Action Required" notification about Privileged Intents approval in the application list.

#.  Click on the notification to open that application's Bot page.
#.  Click the "Get Started" button:

    .. image:: /.resources/intents/action_required_bot_tab.png
        :alt: The "Action Required" notification about Privileged Intents approval on the application's Bot tab.

----

Below you'll find sample answers for the questions in the review. Please note that these answers
are based on our interpretation of Discord's requirements and, while we've successfully used them
to receive the intents ourselves, it is not guaranteed that your application will be approved
when using these verbatim. Depending on what core features of Red and what 3rd-party you are using,
you might have to use different examples from the ones we've provided.

.. admonition:: Additional information

    Before answer to each question, there's a box like this one with information on
    how you may need to adjust the answer to apply to your bot.

Application Details
~~~~~~~~~~~~~~~~~~~

"What does your application do? Please be as detailed as possible [...]"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    | This answer lists features from many core cogs:
    | Audio, Cleanup, Economy, Filter, Mod, ModLog, Reports, Streams, Trivia, and Warnings

    This answer may need to be adjusted to include features from 3rd-party cogs you are using
    and exclude any features from the core cogs that are not loaded.

| Red is a multi-function bot that allows its users to:
| - carry out moderation actions (warnings, kick, ban, softban, hackban, chat cleanup, viewing information about members)
| - keep records of infractions through its moderation log
| - perform automated moderation actions - message, nickname, and user status filtering/warning
| - maintain a user report system for their server (mod-mail)
| - play games with others - trivia, slots
| - play music in voice channels from online audio streams
| - configure stream alerts (Twitch, YouTube, Picarto)
| - setup custom commands in servers that display text (e.g. FAQ answers) which other users can run

This is a self-hosted instance of the following open-source bot:
https://github.com/Cog-Creators/Red-DiscordBot

Do you have a public Privacy Policy telling your users about their data usage?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    You are required to have a privacy policy so this must be "Yes".

Yes

Where is your Privacy Policy available?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    This answer can be kept as is, just make sure to include a link to your privacy policy in the
    description of your application to have it show in the About Me section of your bot's profile.

    This can be done in the "General Information" tab of your bot application.

The link to privacy policy is included within the bot's bio.

Please share a link to your Privacy Policy.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    Replace ``https://example.github.io/link-to-your-privacy-policy/`` in this answer
    with a link to your privacy policy.

``https://example.github.io/link-to-your-privacy-policy/``

Privileged Gateway Intents
~~~~~~~~~~~~~~~~~~~~~~~~~~

Which intents are you applying for, if any?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    Check the intents that you are actually applying for.

| ☑️ Server Members Intent
| ⃣ Presence Intent
| ☑️ Message Content Intent

Server Members Intent
~~~~~~~~~~~~~~~~~~~~~

Why do you need the Guild Members intent?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    The examples in this answer are based on specific core cogs:

    - Mod - tracking username changes (``[p]userinfo``, ``[p]names``, ``[p]modset trackallnames/tracknicknames``)
    - Mutes - tracking when member rejoins a server to reapply roles
    - Filter - auto-moderation of user's nicknames (``[p]filter names``, ``[p]filterset defaultname``)

    The first two should stand on their own, while the last is likely to be considered
    as something that Discord's native AutoMod API supports and would not be enough
    without presenting other examples.

    You may need to adjust this answer to include relevant features from 3rd-party cogs
    you are using and exclude any features from the core cogs that are not loaded.

| The bot has a few features that depend on guild member data:
| - tracking when user's username, global display name, or nickname changes to keep a short history of them that can be viewed by server staff
| - tracking when member rejoins a server to reapply relevant roles to them
| - auto-moderation of user's nicknames

Please provide links to screenshots and/or videos that demonstrate your use case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    Same as for the previous answer:

    These are based on Mod and Mutes core cogs.

    You may need to adjust this answer to include relevant features from 3rd-party cogs
    you are using and exclude any features from the core cogs that are not loaded.

| Example use of a command that shows member's previous names:
| :doclink:`intent-examples/userinfo-previous-names.png`

| Example from audit log of roles being applied on rejoin:
| :doclink:`intent-examples/mutes-role-reapply-audit-log.png`

Are you storing any API Data off-platform (outside of Discord)?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    Since user IDs likely fall under "API Data", you may end up storing API Data
    even without having a single cog loaded so there should be no scenario
    in which you'd answer "No" to this question.

Yes

Are you storing API Data for 30 days or less?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    The data is stored as long as it is relevant which generally is longer than 30 days.
    There should be no scenario in which you'd answer "Yes" to this question.

No

Are you encrypting the data that you store at rest, as is required by our developer policy?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    Discord Developer Terms of Service require that the data that you store is encrypted at rest,
    so you'll be automatically denied the intents, if you answer "No" to this.

    If you're hosting your bot at a respectable server provider, it's likely that your server's
    data is already encrypted at rest. You can consult your provider's documentation to make sure.

    If you're hosting your bot on your own system, you'll need to handle this yourself.
    Generally, data-at-rest encryption means using full disk encryption on your system.
    The details are beyond this documentation but you should be able to search for these terms
    combined with the OS you are using to get some information on this topic.

Yes

Message Content Intent
~~~~~~~~~~~~~~~~~~~~~~

Can users opt-out of having their message content data tracked?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    Discord does not require you to provide an option to opt-out of tracking message content data
    and this data is often needed for moderation purposes, where opting-out would allow for abuse.

No

Are you storing message content data off-platform (outside of Discord)?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    None of the core cogs store message content data off-platform.

    If any of the 3rd-party cogs that you are using store message content data, you should adjust
    this answer accordingly. Answering "Yes" will require answering the same extra questions
    as the ones that were asked for the Server Members Intent - you just need to enter
    the exact same answers as you did for that intent.

No

Will the message content data be used to train machine learning or AI Models?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    None of the core cogs use message content data to train machine learning or AI Models.

    If any of the 3rd-party cogs that you are using do this, you should adjust this answer
    accordingly. Answering "Yes" will require that you include information on how such models
    would be used in the next two questions.

No

Why do you need the Message Content intent?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. admonition:: Additional information

    The examples in this answer are based on specific core cog functionality:

    - Cleanup - features that allow users to cleanup messages (``[p]cleanup duplicates``, ``[p]cleanup text``)
    - Mod - auto-deletion of repeated messages (``[p]modset deleterepeats``)

    You may need to adjust this answer to include relevant features from 3rd-party cogs
    you are using and exclude any features from the core cogs that are not loaded.

| The bot includes features that allow users to cleanup messages in a channel.
  Some of those commands have to filter by the message's content:
| - cleaning up spam (duplicate messages sent recently in a channel)
| - cleaning up messages containing the specified text

Other features that also need the message content intent include automatic message moderation - in particular,
preventing a user from spamming the same message many times which Discord's AutoMod does not reliably block
when using the "Block Suspected Spam Content" rule.

Please provide links to screenshots and/or videos that demonstrate your use case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| Example of cleaning duplicated messages manually by a moderator:
| :doclink:`intent-examples/cleanup-spam-example-before.png`
| :doclink:`intent-examples/cleanup-spam-example-triggered.png`
| :doclink:`intent-examples/cleanup-spam-example-after.png`

| Example of cleaning messages containing specified text:
| :doclink:`intent-examples/cleanup-text-example-before.png`
| :doclink:`intent-examples/cleanup-text-example-triggered.png`
| :doclink:`intent-examples/cleanup-text-example-after.png`

----

.. _intents-disabling:

How to change my instance's enabled privileged intents?
-------------------------------------------------------

Windows
~~~~~~~

To change your instance's enabled privileged intents, you can follow these steps:

#. Shut your bot down.
#. Activate your venv with the following command:

    .. prompt:: batch

        "%userprofile%\redenv\Scripts\activate.bat"
#. Edit your instance with this command:

    .. prompt:: batch
        :prompts: (redenv) C:\\>

        redbot --edit <your instance name>

    You'll be asked several questions. One of them will be about changing the enabled privileged intents,
    answer "yes" to it and then answer "yes" to questions about the intents whose current state you want to change:

    .. code::

        Guild Presences privileged intent is currently disabled. Do you want to enable it?: [y/N] y
        Guild Presences privileged intent has been enabled.
        Guild Members privileged intent is currently enabled. Do you want to disable it?: [y/N] 
        Message Content privileged intent is currently enabled. Do you want to disable it?: [y/N] 

#. After you finish with the ``redbot --edit`` command, start your bot.

Linux & Mac
~~~~~~~~~~~

To change your instance's enabled privileged intents, you can follow these steps:

#. Shut your bot down.
#. Activate your virtual environment.
  
    If you used ``venv`` for your virtual environment, use:

    .. prompt:: bash

        source ~/redenv/bin/activate

#. Edit your instance with this command:

    .. prompt:: bash
        :prompts: (redenv) $

        redbot --edit <your instance name>

    You'll be asked several questions. One of them will be about changing the enabled privileged intents,
    answer "yes" to it and then answer "yes" to questions about the intents whose current state you want to change:

    .. code::

        Guild Presences privileged intent is currently disabled. Do you want to enable it?: [y/N] y
        Guild Presences privileged intent has been enabled.
        Guild Members privileged intent is currently enabled. Do you want to disable it?: [y/N] 
        Message Content privileged intent is currently enabled. Do you want to disable it?: [y/N] 

#. After you finish with the ``redbot --edit`` command, start your bot.
