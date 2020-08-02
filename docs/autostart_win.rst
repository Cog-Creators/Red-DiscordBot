.. windows service guide

==================================
Setting up auto-restart on Windows
==================================

-------------------------------
Downloading NSSM via Chocolatey
-------------------------------

.. note:: This assumes you already have chocolatey installed. 
          If not, you may install it or follow the manual instructions for getting NSSM.

To install via Chocolatey, search "powershell" in the start menu,
right-click on it and then click "Run as administrator"

Then run the following command:

.. code-block:: none

    choco install nssm -y

------------------------
Manually installing NSSM
------------------------

Go to `<https://nssm.cc/download>`_ and download the latest release. Once the download
is finished, open File Explorer, navigate to the drive Windows is installed on, and 
create a folder called :code:`nssm`. Then navigate to your Downloads folder, and move 
:code:`nssm.exe` to :code:`C:\nssm`.

Then open Powershell as administrator (search "powershell" in the start menu, then right-click and 
click "Run as administrator") and run the following commands to add NSSM to your path.

.. code-block:: none

    $oldPath = (Get-Itemproperty -path 'hklm:\system\currentcontrolset\control\session manager\environment' -Name Path).Path
    $newPath = $oldPath + ";C:\nssm"
    Set-ItemProperty -path 'hklm:\system\currentcontrolset\control\session manager\environment' -Name Path -Value $newPath

Once finished, log out and back in to ensure the changes take effect.

----------------------
Setting up the service
----------------------

To create the service, run the following command:

.. code-block:: none

    . $env:USERPROFILE\redenv\Scripts\activate.ps1
    nssm install redbot $(Get-Command python).Definition -O -m redbot <instance name> --no-prompt

replacing <instance name> with the name of the instance.

Then run the following set of commands one at a time:

.. code-block:: none

    nssm set redbot AppExit 0 Exit
    nssm set redbot AppStopMethodConsole 10000
    nssm set redbot AppRestartDelay 15000
    nssm set redbot AppStdout $Env:USERPROFILE\redbot.log
    nssm set redbot AppStderr $Env:USERPROFILE\redbot.log
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
