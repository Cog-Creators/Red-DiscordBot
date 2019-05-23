.. launchd guide

==============================
Setting up auto-restart on Mac
==============================

-----------------------
Creating the plist file
-----------------------

:code:`sudo -e /Library/LaunchDaemons/red.plist`

Paste the following and replace all instances of :code:`username` with the username your bot is running under (hopefully not root) and replace :code:`/path/to/redbot` with the path to :code:`redbot` and :code:`instance-name` with your instance name:

.. code-block:: none

    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>red</string>
            <key>ProgramArguments</key>
            <array>
                <string>/path/to/redbot</string>
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
            <key>UserName</key>
            <string>username</string>
            <key>GroupName</key>
            <string>username</string>
            <key>InitGroups</key>
            <true/>
        </dict>
    </plist>

Save and exit.

-----------------
Loading the plist
-----------------

Run the following:

:code:`sudo launchctl load /Library/LaunchDaemons/red.plist`

If you need to shutdown the bot, you can use the ``[p]shutdown`` command or
type the following command in the terminal:

:code:`sudo launchctl stop red`
