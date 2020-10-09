.. _permissions:

===========
Permissions
===========

This is the cog guide for the permissions cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load permissions

.. _permissions-usage:

-----
Usage
-----

Customise permissions for commands and cogs.


.. _permissions-commands:

--------
Commands
--------

.. _permissions-command-permissions:

^^^^^^^^^^^
permissions
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]permissions 

**Description**

Command permission management tools.

.. _permissions-command-permissions-explain:

^^^^^^^
explain
^^^^^^^

**Syntax**

.. code-block:: none

    [p]permissions explain 

**Description**

Explain how permissions works.

.. _permissions-command-permissions-setdefaultserverrule:

^^^^^^^^^^^^^^^^^^^^
setdefaultserverrule
^^^^^^^^^^^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions setdefaultserverrule <allow_or_deny> <cog_or_command>

**Description**

Set the default rule for a command in this server.

This is the rule a command will default to when no other rule
is found.

`<allow_or_deny>` should be one of "allow", "deny" or "clear".
"clear" will reset the default rule.

`<cog_or_command>` is the cog or command to set the default
rule for. This is case sensitive.

.. _permissions-command-permissions-addglobalrule:

^^^^^^^^^^^^^
addglobalrule
^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions addglobalrule <allow_or_deny> <cog_or_command> <who_or_what>...

**Description**

Add a global rule to a command.

`<allow_or_deny>` should be one of "allow" or "deny".

`<cog_or_command>` is the cog or command to add the rule to.
This is case sensitive.

`<who_or_what>` is one or more users, channels or roles the rule is for.

.. _permissions-command-permissions-canrun:

^^^^^^
canrun
^^^^^^

**Syntax**

.. code-block:: none

    [p]permissions canrun <user> <command>

**Description**

Check if a user can run a command.

This will take the current context into account, such as the
server and text channel.

.. _permissions-command-permissions-addserverrule:

^^^^^^^^^^^^^
addserverrule
^^^^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions addserverrule <allow_or_deny> <cog_or_command> <who_or_what>...

**Description**

Add a rule to a command in this server.

`<allow_or_deny>` should be one of "allow" or "deny".

`<cog_or_command>` is the cog or command to add the rule to.
This is case sensitive.

`<who_or_what>` is one or more users, channels or roles the rule is for.

.. _permissions-command-permissions-removeserverrule:

^^^^^^^^^^^^^^^^
removeserverrule
^^^^^^^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions removeserverrule <cog_or_command> <who_or_what>...

**Description**

Remove a server rule from a command.

`<cog_or_command>` is the cog or command to remove the rule
from. This is case sensitive.

`<who_or_what>` is one or more users, channels or roles the rule is for.

.. _permissions-command-permissions-removeglobalrule:

^^^^^^^^^^^^^^^^
removeglobalrule
^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions removeglobalrule <cog_or_command> <who_or_what>...

**Description**

Remove a global rule from a command.

`<cog_or_command>` is the cog or command to remove the rule
from. This is case sensitive.

`<who_or_what>` is one or more users, channels or roles the rule is for.

.. _permissions-command-permissions-setdefaultglobalrule:

^^^^^^^^^^^^^^^^^^^^
setdefaultglobalrule
^^^^^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions setdefaultglobalrule <allow_or_deny> <cog_or_command>

**Description**

Set the default global rule for a command.

This is the rule a command will default to when no other rule
is found.

`<allow_or_deny>` should be one of "allow", "deny" or "clear".
"clear" will reset the default rule.

`<cog_or_command>` is the cog or command to set the default
rule for. This is case sensitive.

.. _permissions-command-permissions-acl:

^^^
acl
^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl 

**Description**

Manage permissions with YAML files.

.. _permissions-command-permissions-acl-yamlexample:

^^^^^^^^^^^
yamlexample
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]permissions acl yamlexample 

**Description**

Sends an example of the yaml layout for permissions

.. _permissions-command-permissions-acl-getserver:

^^^^^^^^^
getserver
^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl getserver 

**Description**

Get a YAML file detailing all rules in this server.

.. _permissions-command-permissions-acl-setglobal:

^^^^^^^^^
setglobal
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl setglobal 

**Description**

Set global rules with a YAML file.

**WARNING**: This will override reset *all* global rules
to the rules specified in the uploaded file.

This does not validate the names of commands and cogs before
setting the new rules.

.. _permissions-command-permissions-acl-updateserver:

^^^^^^^^^^^^
updateserver
^^^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl updateserver 

**Description**

Update rules for this server with a YAML file.

This won't touch any rules not specified in the YAML
file.

.. _permissions-command-permissions-acl-setserver:

^^^^^^^^^
setserver
^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl setserver 

**Description**

Set rules for this server with a YAML file.

**WARNING**: This will override reset *all* rules in this
server to the rules specified in the uploaded file.

.. _permissions-command-permissions-acl-updateglobal:

^^^^^^^^^^^^
updateglobal
^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl updateglobal 

**Description**

Update global rules with a YAML file.

This won't touch any rules not specified in the YAML
file.

.. _permissions-command-permissions-acl-getglobal:

^^^^^^^^^
getglobal
^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl getglobal 

**Description**

Get a YAML file detailing all global rules.

.. _permissions-command-permissions-clearglobalrules:

^^^^^^^^^^^^^^^^
clearglobalrules
^^^^^^^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions clearglobalrules 

**Description**

Reset all global rules.

.. _permissions-command-permissions-clearserverrules:

^^^^^^^^^^^^^^^^
clearserverrules
^^^^^^^^^^^^^^^^

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions clearserverrules 

**Description**

Reset all rules in this server.
