.. systemd service guide

==============================================
Setting up auto-restart using systemd on Linux
==============================================

-------------------------
Creating the service file
-------------------------

Create the new service file:

:code:`sudo nano /etc/systemd/system/red@.service`

Paste the following and replace all instances of :code:`username` with the username your bot is running under (hopefully not root):

.. code-block:: none

    [Unit]
    Description=%I redbot
    After=multi-user.target

    [Service]
    ExecStart=/home/username/.local/bin/redbot %I --no-prompt
    User=username
    Group=username
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

.. note:: This same file can be used to start as many instances of the bot as you wish, without creating more service files, just start and enable more services and add any bot instance name after the **@**

To start the bot, run the service and add the instance name after the **@**:

:code:`sudo systemctl start red@instancename`

To set the bot to start on boot, you must enable the service, again adding the instance name after the **@**:

:code:`sudo systemctl enable red@instancename`

To view Red’s log, you can acccess through journalctl:

:code:`sudo journalctl -u red@instancename`
