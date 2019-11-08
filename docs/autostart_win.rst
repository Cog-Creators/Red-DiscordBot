.. windows service guide

==================================
Setting up auto-restart on Windows
==================================

-------------------------------
Downloading NSSM via Chocolatey
-------------------------------

.. note:: This assumes you already have chocolatey installed. 
          If not, you may install it or follow the manual instructions for getting NSSM

To install via Chocolatey, search "powershell" in the start menu,
right-click on it and then click "Run as administrator"

Then run the following command:

.. code-block:: none

    choco install nssm -y

------------------------
Manually installing NSSM
------------------------

To be written

----------------------
Setting up the service
----------------------

To create the service, run the following command:

.. code-block:: none

    nssm install redbot $(Get-Command redbot).Definition <instance name> --no-prompt

replacing <instance name> with the name of the instance.

Then run the following set of commands one at a time:

.. code-block:: none

    nssm set redbot AppExit 0 Exit
    nssm set redbot AppStopMethodConsole 10000
    nssm set redbot AppRestartDelay 15000
    nssm set redbot AppStdout $Env:USERPROFILE\red-stdout.log
    nssm set redbot AppStderr $Env:USERPROFILE\red-stderr.log
    nssm set redbot AppNoConsole 1

The above commands change a number of settings for the service including:
- Ensuring that when ``[p]shutdown`` is run, the service doesn't attempt to restart
- Ensuring that if Control-C is pressed for the process, nssm waits 10 seconds
- Setting a 15 second delay for service restart
- Setting a couple of log files for the service
- Disabling the console window

Now that the service has been configured, run the following command:

.. code-block:: none

    nssm set redbot ObjectName $Env:COMPUTERNAME\$Env:USERNAME <password>

replacing <password> with the password you use to login to your computer. This
sets the service to run under your user account so it can find your instances.

--------------------
Starting the service
--------------------

Run the following command:

.. code-block:: none

    nssm start redbot

If you see 

.. code-block:: none

    redbot: START: The operation completed successfully.

then the service started successfully and the bot will be online!