.. centos install guide

==========================
Installing Red on CentOS 7
==========================

.. warning:: For safety reasons, DO NOT install Red with a root user. Instead, `make a new one <https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/4/html/Step_by_Step_Guide/s1-starting-create-account.html>`_.

---------------------------
Installing pre-requirements
---------------------------

.. code-block:: none

    yum -y groupinstall development
    yum -y install https://centos7.iuscommunity.org/ius-release.rpm
    yum -y install yum-utils wget which python36u python36u-pip python36u-devel openssl-devel libffi-devel git java-1.8.0-openjdk

--------------
Installing Red
--------------

Without audio:

:code:`pip3 install -U --process-dependency-links red-discordbot --user`

With audio:

:code:`pip3 install -U --process-dependency-links red-discordbot[voice] --user`

To install the development version (without audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot --user`

To install the development version (with audio):

:code:`pip3 install -U --process-dependency-links git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop#egg=red-discordbot[voice] --user`

----------------------
Setting up an instance
----------------------

Run :code:`redbot-setup` and follow the prompts. It will ask first for where you want to
store the data (the default is :code:`~/.local/share/Red-DiscordBot`) and will then ask
for confirmation of that selection. Next, it will ask you to choose your storage backend
(the default here is JSON). It will then ask for a name for your instance. This can be
anything as long as it does not contain spaces; however, keep in mind that this is the
name you will use to run your bot, and so it should be something you can remember.

-----------
Running Red
-----------

Run :code:`redbot <your instance name>` and run through the initial setup. This will ask for
your token and a prefix.
