.. mac install guide

=====================
Installing Red on Mac
=====================

---------------------------
Installing pre-requirements
---------------------------

* Install Brew
    * In Finder or Spotlight, search for and open terminal. In the window that will open, paste this:
      :code:`/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
      and press enter.
* After the installation, install the required packages by pasting the commands and pressing enter, one-by-one:
    * :code:`brew install python3 --with-brewed-openssl`
    * :code:`brew install git`
    * :code:`brew install ffmpeg --with-ffplay`
    * :code:`brew install opus`

--------------
Installing Red
--------------

To install Red, run :code:`pip3 install -U --process-dependency-links red-discordbot[voice]`

----------------------
Setting up an instance
----------------------

To set up an instance, run :code:`redbot-setup` and follow the steps there, providing the requested information
or accepting the defaults. Keep in mind that the instance name will be the one you use when running the bot, so
make it something you can remember

-----------
Running Red
-----------

Run :code:`redbot <your instance name>` and go through the initial setup (it will ask for the token and a prefix).