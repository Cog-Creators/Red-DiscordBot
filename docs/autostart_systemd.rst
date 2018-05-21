.. systemd service guide

==============================================
Setting up auto-restart using systemd on Linux
==============================================

.. warning:: This guide assumes you have installed the bot under a new user using the :code:`--user`
   flag, if you did not, you will need to correct the :code:`redbot` path under :code:`ExecStart`
   (obtainable by using :code:`which redbot`).

-------------------------
Creating the service file
-------------------------

Create the new service file:

:code:`nano ~/.config/systemd/user/red@.service`

Paste the following and replace all instances of :code:`username` with the username your bot is
running under (hopefully not root):

.. code-block:: none

    [Unit]
    Description=%I - redbot
    After=multi-user.target

    [Service]
    ExecStart=/home/username/.local/bin/redbot %I --no-prompt
    Type=idle
    Restart=always
    RestartSec=15
    RestartPreventExitStatus=0

    [Install]
    WantedBy=multi-user.target

Save and exit :code:`ctrl + O; enter; ctrl + x`

---------------------------------
Starting and enabling the service
---------------------------------

.. note:: This same file can be used to start as many instances of the bot as you wish, without
   creating more service files, just start and enable more services and add any bot instance name
   after the **@**

To start the bot, run the service and add the instance name after the **@**:

:code:`systemctl start red@instancename --user`

To set the bot to start on boot, you must enable the service, again adding the instance name after
the **@**:

:code:`systemctl enable red@instancename --user`

To view Red’s log, you can acccess through journalctl:

:code:`journalctl -u red@instancename --user`
