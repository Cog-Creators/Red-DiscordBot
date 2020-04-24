============
Updating Red
============

Updating to the latest version of Red has several benefits:

- New features and improvements are added.
- Bugs are fixed.
- Your bot is safe from security vulnerabilities that have been found.

Here are some things to consider to help make your upgrade as smooth as possible.

.. note::

    If you're developing for Red, you should also look for "Breaking changes" sections in release notes for each minor (X.Y.0) version that's been released since you last updated Red.

Updating differs depending on the version you currently have. Next sections will explain how to upgrade to latest version of Red (|version|) from the version that is in the header of the section.


Red 3.2.0 or newer
******************

Windows
-------

If you have Red 3.2.0 or newer, all you have to do to upgrade Red is running 2 commands.

1. Activate your venv with the following command:

    .. code:: none

        "%userprofile%\redenv\Scripts\activate.bat"

2. Update Red with this command:

    .. code:: none

        python -m pip install -U Red-DiscordBot

.. attention::

    If you're using PostgreSQL data backend, replace ``Red-DiscordBot`` in the second command with ``Red-DiscordBot[postgres]``

Linux & Mac
-----------

If you have Red 3.2.0 or newer, all you have to do to upgrade Red is running 2 commands.

1. Activate your virtual environment.
  
    If you used ``venv`` for your virtual environment, use:

    .. code:: none

        source ~/redenv/bin/activate

    If you used ``pyenv`` for your virtual environment, use:

    .. code:: none

        pyenv shell <name>

2. Update Red with this command:

    .. code:: none

        python -m pip install -U Red-DiscordBot

.. attention::

    If you're using PostgreSQL data backend, replace ``Red-DiscordBot`` in the second command with ``Red-DiscordBot[postgres]``


Red 3.1.X
*********

If you have Red 3.1.X, you will need to follow the install instructions for your operating system:

- `Windows <install_windows>`
- `Linux & Mac <install_linux_mac>`

Follow every step to ensure you have all dependencies up-to-date and only skip ``redbot-setup`` step as you already have a bot instance.

If you already have Red installed in a virtual environment, you will need to delete it before starting this process.

.. attention::

    Red 3.2 dropped support for the MongoDB driver

     - If you were not using the MongoDB driver, this does not affect you.
     - If you were using a 3rd party cog which required MongoDB, it probably still does.
     - If you were using the MongoDB driver, **prior to launching your instance after update**,
       you will need to run the following commands to convert:

         .. code::

           python -m pip install dnspython~=1.16.0 motor~=2.0.0 pymongo~=3.8.0
           redbot-setup convert [instancename] json


Red 3.0.2 and older
*******************

.. important::

    Red 3.2 dropped support for the MongoDB driver

     - If you were not using the MongoDB driver, this does not affect you.
     - If you were using a 3rd party cog which required MongoDB, it probably still does.
     - If you were using the MongoDB driver, **prior to updating**, you will need to convert your data to JSON backend,
       using following command:

         .. code::

           redbot-setup --edit

If you have Red 3.0.2 or older, you will need to follow the install instructions for your operating system:

- `Windows <install_windows>`
- `Linux & Mac <install_linux_mac>`

Follow every step to ensure you have all dependencies up-to-date and only skip ``redbot-setup`` step as you already have a bot instance.

If you already have Red installed in a virtual environment, you will need to delete it before starting this process.
