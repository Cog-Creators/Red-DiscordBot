.. pm2 service guide

==============================================
Setting up auto-restart using pm2 on Linux
==============================================

.. note:: This guide is for setting up PM2 on a Linux environment. This guide assumes that you already have a working Red instance.

--------------
Installing PM2
--------------

Start by installing Node.JS and NPM via your favorite package distributor. From there run the following command:

.. prompt:: bash

    npm install pm2 -g

After PM2 is installed, run the following command to enable your Red instance to be managed by PM2. Replace the brackets with the required information.
You can add additional Red based arguments after the instance name, such as :code:`--dev`.

.. prompt:: bash

    pm2 start "<path>" --name "<app_name>" -- -O -m redbot <instance_name> --no-prompt

**Arguments to replace**

- ``<app_name>`` - A name to identify the bot within pm2, this is not your Red instance.

- | ``<path>`` - The location of your Python interpreter.
  | To find out where that is, use the proper set of commands:

  .. prompt:: bash
      :prompts: $,(redenv) $
      :modifiers: auto

      # If redbot is installed in a venv
      $ source ~/redenv/bin/activate
      (redenv) $ which python

      # If redbot is installed in a pyenv virtualenv
      $ pyenv shell <virtualenv_name>
      (redenv) $ pyenv which python

- ``<instance_name>`` - The name of your Red instance.

------------------------------
Ensuring that PM2 stays online
------------------------------

To make sure that PM2 stays online and persistence between machine restarts, run the following commands:

.. prompt:: bash

    pm2 save
    pm2 startup
