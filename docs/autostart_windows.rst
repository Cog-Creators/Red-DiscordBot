.. _autostart_windows:

==============================================
Setting up auto-restart on Windows
==============================================

.. note:: This guide assumes that you already have a working Red instance.

This script will setup windows schedule task to start the bot when the computer starts, it also checks for updates when the bot starts or is restarted by command ``[p]restart``.

-------------------------
Creating the batch file
-------------------------

.. important:: If you followed the `install_windows` your virtual environment should be ``"%userprofile%\redenv"``.   
 
Create a new text file in your virtual environment directory named eg ``autostart.bat`` open it in any text editor and paste the following script. 
Then replace <path to redenv> with eg ``E:\redenv`` the directory where you installed the virtual environment and <your instance name> to the instance name from the redbot setup process eg ``MyBot`` 

.. code-block:: batch
    
    @ECHO OFF
    SET venv=<path to redenv>
    SET instance_name=<your instance name>
    SET auto_update=TRUE
    SET setup_tasks=TRUE

    :SETUP_TASKS
    IF %setup_tasks% EQU TRUE (
        ECHO Setting up windows scheduler task.
        schtasks /query /TN "RedBot\autostart" >NUL 2>&1 || powershell Start-Process -Verb RunAs cmd.exe -Args '/c', 'SCHTASKS /CREATE /SC ONSTART /TN "RedBot\autostart" /TR "%venv%\%~n0%~x0" /F'
    )

    :START
    PUSHD %venv%    

    :ACTIVATE_VENV
    CALL "%venv%\Scripts\activate.bat"

    :UPDATE
    IF %auto_update% EQU TRUE (
        ECHO Checking for updates.
        python -m pip install -U pip setuptools wheel
        python -m pip install -U Red-DiscordBot
    )

    ECHO starting redbot.
    CALL python -O -m redbot %instance_name%

    IF %ERRORLEVEL% EQU 26 (
        GOTO :START
    )

.. note:: If you are getting **Access denied** when scheduled task is trying to setup it's task, try run it as administrator. Right click on the file and select **Run as administarator**.

.. important:: Do not forget to change ``<path to redenv>`` and ``<your instance name>`` in the script before use.
