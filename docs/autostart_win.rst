.. launchd guide

==================================
Setting up auto-restart on Windows
==================================

-----------------------
Creating the bat file
-----------------------

Create a .bat script and paste the following into it

.. code-block:: none

    cd %userprofile%\redenv\Scripts && CALL activate.bat && cd %userprofile%\redenv\Scripts && cls && redbot <name of your instance>

-------------------------------
Setting Redbot to autostart
-------------------------------

To start the bot and set it to start on boot, press the windows key + R and type in **shell:startup** 
create a shortcut of the .bat file we create earlier and place it in this new foolder that popped up.
your all set redbot will auto start whenever u reboot or turn on your pc.
if u wanna start it like normal you can just run the exe file like you would a standard program.

--------------------------------------
Disabling Redbot's autostart function
--------------------------------------

To do this all you have to do is delete the shortcut we place in the autostart folder.
