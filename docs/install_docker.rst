.. _linux-docker-install-guide:

========================
Installing Red on Docker
========================

.. note::

    For further information look at https://docs.docker.com/

------------------------------------
Installing docker and docker-compose
------------------------------------

Run to install Docker and Docker-Compose:

.. code-block:: none

    sudo curl -sSL https://get.docker.com | sh
    sudo pip install docker-compose

Additional commands to allow running docker without sudo:

.. code-block:: none

    sudo groupadd docker
    sudo usermod -aG docker $USER

Configure Docker to run on startup:

.. code-block:: none

    sudo systemctl enable docker
    
--------------
Installing Red
--------------

Download the ``docker-compose.yml``. 

.. note::

    If you are running on arm change ``Cog-Creators/Red-DiscordBot:latest`` to
    ``Cog-Creators/Red-DiscordBot:latest-arm``.

To download and run the image run the following command in the directory of ``docker-compose.yml``:

.. code-block:: none

    docker-compose up -d


--------------------------
Setting Up and Running Red
--------------------------

After installation, set up your instance with the following command:

.. code-block:: none

    docker-compose run --rm red-discordbot redbot docker

After that Red will start with docker and onyl needs to be updated from time to time via:

.. code-block:: none

    docker-compose pull && docker-compose up -d
