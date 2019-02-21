.. _installing-in-virtual-environment:

=======================================
Installing Red in a Virtual Environment
=======================================
Virtual environments allow you to isolate red's library dependencies, cog dependencies and python
binaries from the rest of your system. It is strongly recommended you use this if you use python
for more than just Red.

.. _using-venv:

--------------
Using ``venv``
--------------
This is the quickest way to get your virtual environment up and running, as `venv` is shipped with
python.

First, choose a directory where you would like to create your virtual environment. It's a good idea
to keep it in a location which is easy to type out the path to. From now, we'll call it
``path/to/venv/`` (or ``path\to\venv\`` on Windows).

~~~~~~~~~~~~~~~~~~~~~~~~
``venv`` on Linux or Mac
~~~~~~~~~~~~~~~~~~~~~~~~
Create your virtual environment with the following command::

    python3.7 -m venv path/to/venv/

And activate it with the following command::

    source path/to/venv/bin/activate

.. important::

    You must activate the virtual environment with the above command every time you open a new
    shell to run, install or update Red.

Continue reading `below <after-activating-virtual-environment>`.

~~~~~~~~~~~~~~~~~~~
``venv`` on Windows
~~~~~~~~~~~~~~~~~~~
Create your virtual environment with the following command::

    python -m venv path\to\venv\

And activate it with the following command::

    path\to\venv\Scripts\activate.bat

.. important::

    You must activate the virtual environment with the above command every time you open a new
    Command Prompt to run, install or update Red.

Continue reading `below <after-activating-virtual-environment>`.

.. _using-pyenv-virtualenv:

--------------------------
Using ``pyenv virtualenv``
--------------------------

.. note::

    This is for non-Windows users only.

Using ``pyenv virtualenv`` saves you the headache of remembering where you installed your virtual
environments. If you haven't already, install pyenv with `pyenv-installer`_.

First, ensure your pyenv interpreter is set to python 3.7.0 or greater with the following command::

    pyenv version

Now, create a virtual environment with the following command::

    pyenv virtualenv <name>

Replace ``<name>`` with whatever you like. If you forget what you named it, use the command ``pyenv
versions``.

Now activate your virtualenv with the following command::

    pyenv shell <name>

.. important::

    You must activate the virtual environment with the above command every time you open a new
    shell to run, install or update Red.

Continue reading `below <after-activating-virtual-environment>`.

.. _pyenv-installer: https://github.com/pyenv/pyenv-installer/blob/master/README.rst

----

.. _after-activating-virtual-environment:

Once activated, your ``PATH`` environment variable will be modified to use the virtual
environment's python executables, as well as other executables like ``pip``.

From here, install Red using the commands listed on your installation guide (`Windows
<installing-red-windows>` or `Non-Windows <installing-red-linux-mac>`).

.. note::

    The alternative to activating the virtual environment each time you open a new shell is to
    provide the full path to the executable. This will automatically use the virtual environment's
    python interpreter and installed libraries.

--------------------------------------------
Virtual Environments with Multiple Instances
--------------------------------------------
If you are running multiple instances of Red on the same machine, you have the option of either
using the same virtual environment for all of them, or creating separate ones.

.. note::

    This only applies for multiple instances of V3. If you are running a V2 instance as well,
    You **must** use separate virtual environments.

The advantages of using a *single* virtual environment for all of your V3 instances are:

- When updating Red, you will only need to update it once for all instances (however you will still need to restart all instances for the changes to take effect)
- It will save space on your hard drive

On the other hand, you may wish to update each of your instances individually.

.. important::

    Windows users with multiple instances should create *separate* virtual environments, as
    updating multiple running instances at once is likely to cause errors.
