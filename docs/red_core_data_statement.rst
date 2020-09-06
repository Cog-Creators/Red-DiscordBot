.. Red Core Data Statement

=====================
Red and End User Data
=====================

Notes for everyone
******************

What data Red collects
----------------------

Red and the cogs included with it collect some amount of data
about users for the bot's normal operations. 

The bot will keep track of a short history of usernames/nicknames. It will also
remember which actions were taken using your Discord account (such as creating a playlist)
as well as the content of specific messages used directly as commands for the bot
(such as reports sent to servers).

By default, Red will not collect any more data than it needs, and will not use it
for anything other than the portion of the Red's functionality that necessitated it.

3rd party extensions may store additional data beyond what Red does by default.
You can use the command ``[p]mydata 3rdparty``
to view statements about how extensions use your data made by the authors of 
the specific 3rd party extensions an instance of Red has installed.

How can I delete data Red has about me?
---------------------------------------

The command ``[p]mydata forgetme`` provides a way for users to remove
large portions of their own data from the bot. This command will not
remove operational data, such as a record that your
Discord account was the target of a moderation action.

3rd party extensions to Red are able to delete data when this command
is used as well, but this is something each extension must implement.
If a loaded extension does not implement this, the user will be informed.

Additional Notes for Bot Owners and Hosts
*****************************************

How to comply with a request from Discord Trust & Safety
--------------------------------------------------------

There are a handful of these available to bot owners in the command group
``[p]mydata ownermanagement``.

The most pertinent one if asked to delete data by a member of Trust & Safety
is

``[p]mydata ownermanagement processdiscordrequest`` 

This will cause the bot to get rid of or disassociate all data
from the specified user ID. 

.. warning::

    You should not use this unless
    Discord has specifically requested this with regard to a deleted user.
    This will remove the user from various anti-abuse measures.
    If you are processing a manual request from a user, read the next section


How to process deletion requests from users
-------------------------------------------

You can point users to the command ``[p]mydata forgetme`` as a first step.

If users cannot use that for some reason, the command

``[p]mydata ownermanagement deleteforuser``

exists as a way to handle this as if the user had done it themselves.

Be careful about using the other owner level deletion options on behalf of users,
as this may also result in losing operational data such as data used to prevent spam.

What owners and hosts are responsible for
-----------------------------------------

Owners and hosts must comply both with Discord's terms of service and any applicable laws.
Owners and hosts are responsible for all actions their bot takes.

We cannot give specific guidance on this, but recommend that if there are any issues
you be forthright with users, own up to any mistakes, and do your best to handle it.
