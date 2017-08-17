How to install MongoDB for Red - Discord Bot
============================================

MongoDB is optional for Red but you can install it to increase
performances (in fact I don’t know what it does, replace this line with
the real reason. Please). Also I know I had to make a .rst but I made a
.md just to write the doc

Install for Windows
-------------------

1. Install `MongoDB Community Server for Windows`_ with SSL support.

2. Locate the file just downloaded (often in ``/Downloads``), run the
   ``.msi`` file and follow the steps for installation

3. Set up MongoDB by opening a Command Prompt (Win + R : cmd) and type

::

    md /data/db

4. Start MongoDB by typing in a Command Prompt

::

    "C:Program FilesMongoDBServer3.4binmongod.exe"

5. Connect to MongoDB by opening another Command Prompt and type

::

    "C:Program FilesMongoDBServer3.4binmongod.exe"

MongoDB is now running on your computer!

Install for Mac
---------------

1. Open the shell from the directory you want and download the package
   through this command

::

    curl -O https://fastdl.mongodb.org/osx/mongodb-osx-x86_64-3.4.2.tgz

2. Extract the files (same directory)

::

    tar -zxvf mongodb-osx-x86_64-3.4.2.tgz

3. Copy the extracted archive to a directory (will make a directory from
   the current location)

::

    mkdir -p mongodb
    cp -R -n mongodb-osx-x86_64-3.4.2/ mongodb

4. Type the following command to get your current location

   ::

       pwd

and type this command, replacing ``<mongo-path>`` by the output of the
previous command

::

    export PATH=<mongo-path>/bin:$PATH

5. Run MongoDB by creating this folder

   ::

       mkdir -p /data/db

(please ensure that your user account can access this directory, try to
access it using Finder)

and type this command to start it

::

    mongodb

MongoDB is now running on your computer!

Install for Linux
-----------------

Ubuntu
~~~~~~

1. Import the packages by typing this in a shell

::

    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6

2. Create a list file

   1. Ubuntu 12.04

   ::

       echo "deb [ arch=amd64 ] http://repo.mongodb.org/apt/ubuntu precise/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list

   2. Ubuntu 14.04

   ::

       echo "deb [ arch=amd64 ] http://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list

   3. Ubuntu 16.04 or higher

   ::

       echo "deb [ arch=amd64,arm64 ] http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list

3. Reload database

::

    sudo apt-get update

4. Install the packages

::

    sudo apt-get install -y mongodb-org

5. Run MongoDB

::

    sudo service mongod start

6. Check MongoDB had successfully

::

    cat /var/log/mongodb/mongod.log | tail

If you see the line
``[initandlisten] waiting for connections on port <port>``, then MongoDB
is running on your computer!

.. _MongoDB Community Server for Windows: https://www.mongodb.com/download-center#community
