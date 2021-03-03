.. _systemd-service-guide:

==============================================
Setting up auto-restart using systemd on Linux
==============================================

.. note:: This guide is for setting up systemd on a Linux environment. This guide assumes that you already have a working Red instance.

-------------------------
Creating the service file
-------------------------

In order to create the service file, you will first need to know two things, your Linux :code:`username` and your Python :code:`path`

First, your Linux :code:`username` can be fetched with the following command:

.. code-block:: bash

    whoami

Next, your python :code:`path` can be fetched with the following commands:

.. code-block:: bash

    # If redbot is installed in a venv
    source ~/redenv/bin/activate
    which python

    # If redbot is installed in a pyenv virtualenv
    pyenv shell <virtualenv_name>
    pyenv which python

Then create the new service file:

:code:`sudo nano /etc/systemd/system/red@.service`

Paste the following in the file, and replace all instances of :code:`username` with the Linux username you retrieved above, and :code:`path` with the python path you retrieved above.

.. code-block:: none

    [Unit]
    Description=%I redbot
    After=multi-user.target
    After=network-online.target
    Wants=network-online.target

    [Service]
    ExecStart=path -O -m redbot %I --no-prompt
    User=username
    Group=username
    Type=idle
    Restart=always
    RestartSec=15
    RestartPreventExitStatus=0
    TimeoutStopSec=10

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

If you need to shutdown the bot, you can use the ``[p]shutdown`` command or
type the following command in the terminal, still by adding the instance name after the **@**:

:code:`sudo systemctl stop red@instancename`

.. warning:: If the service doesn't stop in the next 10 seconds, the process is killed.
    Check your logs to know the cause of the error that prevents the shutdown.

To view Red’s log, you can acccess through journalctl:

:code:`sudo journalctl -eu red@instancename`
