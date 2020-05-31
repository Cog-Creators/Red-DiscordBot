.. _autostart_windows:

==============================================
Setting up auto-restart on Windows
==============================================

.. note:: This guide assumes that you already have a working Red instance.

This script will setup windows schedule task to start the bot when the computer starts, it also checks for updates when the bot starts or is restarted by command ``[p]restart``.

--------------------------------------
Creating the auto restart batch file
--------------------------------------

.. important:: If you followed the `install_windows` your virtual environment should be ``"%userprofile%\redenv"``.   
 
Create a new text file in your virtual environment directory named eg ``autostart.bat`` open it in any text editor and paste the following script. 
Then replace <path to redenv> with eg ``E:\redenv`` the directory where you installed the virtual environment and <your instance name> to the instance name from the redbot setup process eg ``MyBot`` 

.. code-block:: batch
    
    @ECHO OFF
    SET venv=<path to redenv>
    SET instance_name=<your instance name>

    :START
    PUSHD %venv%    

    :ACTIVATE_VENV
    CALL "%venv%\Scripts\activate.bat"

    ECHO starting redbot.
    CALL python -O -m redbot %instance_name%

    IF %ERRORLEVEL% EQU 26 (
        GOTO :START
    )

.. important:: Do not forget to change ``<path to redenv>`` and ``<your instance name>`` in the script before use.

----------------------------------
Create the windows startup task.
----------------------------------

Open command prompt and run the following command to create a new task that will run the bot on startup. 

.. code-block:: batch

    SCHTASKS /CREATE /SC ONSTART /TN "RedBot\autostart" /TR "<path to redenv>" /F

.. important:: Do not forget to change the ``<path to redenv>``
