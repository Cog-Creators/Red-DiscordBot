.. launchd guide

==============================
Setting up auto-restart on Mac
==============================

-----------------------
Creating the plist file
-----------------------

Start by activating your venv. Then run the following command:

.. code-block:: none

    which python

Copy the output of that command.

Now run :code:`sudo nano /Library/LaunchDaemons/red.plist`

Paste the following and replace the following: 

- all instances of :code:`username` with your Mac username 
- :code:`path` with the path you copied earlier
- :code:`instance-name` with your instance name:

.. code-block:: none

    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>red</string>
            <key>ProgramArguments</key>
            <array>
                <string>path</string>
                <string>-O</string>
                <string>-m</string>
                <string>redbot</string>
                <string>instance-name</string>
                <string>--no-prompt</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>KeepAlive</key>
            <dict>
                <key>SuccessfulExit</key>
                <false/>
            </dict>
            <key>StandardOutPath</key>
            <string>/tmp/red_out.log</string>
            <key>StandardErrorPath</key>
            <string>/tmp/red_err.log</string>
            <key>UserName</key>
            <string>username</string>
            <key>InitGroups</key>
            <true/>
        </dict>
    </plist>

.. note::

    You may add any additional arguments you need to add to the :code:`redbot` command by 
    adding them to the end of the array under :code:`ProgramArguments`

.. note::

    Should you need to view the output from Red (for example: to find error messages that 
    are output to the console to help with support), you can run :code:`nano /tmp/red_out.log` 
    and :code:`nano /tmp/red_err.log` to do so

Save and exit :code:`ctrl + O; enter; ctrl + x`

-----------------
Loading the plist
-----------------

Run the following:

:code:`sudo launchctl load /Library/LaunchDaemons/red.plist`

If you need to shutdown the bot, you can use the ``[p]shutdown`` command or
type the following command in the terminal:

:code:`sudo launchctl stop red`