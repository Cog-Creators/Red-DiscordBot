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

Next you will need to create an .exe file from this .bat script.
To do this I used https://www.battoexeconverter.com/ just download and install it.
After that's done, right click the .bat file and click Compile with Advanced BAT to EXE
This will create an .exe file that does the same thing as the .bat file.
Now this may have seemed completely useless but heres where we we setup the autostart feature.

-------------------------------
Setting Redbot to autostart
-------------------------------

To start the bot and set it to start on boot, press the windows key + R and type in shell:startup
create a shortcut of the exe file we create earlier and place it in this new foolder that popped up.
your all set redbot will auto start whenever u reboot or turn on your pc.
if u wanna start it like normal you can just run the exe file like you would a standard program.

--------------------------------------
Disabling Redbot's autostart function
--------------------------------------

To do this all you have to do is
1: Delete the shortcut we place in the autostart folder.
OR
2: you can press windows and type startup app and hit enter. then turn off the exe.
