------------------------------
Creating a Virtual Environment
------------------------------

.. tip::

    If you want to learn more about virtual environments, see page: `about-venvs`

We require installing Red into a virtual environment. Don't be scared, it's very
straightforward.

**************************
Using ``pyenv virtualenv``
**************************

Using ``pyenv virtualenv`` saves you the headache of remembering where you installed your virtual
environments. This option is only available if you installed Python with pyenv.

First, ensure your pyenv interpreter is set to python 3.8.1 or greater with the following command:

.. prompt:: bash

    pyenv version

Now, create a virtual environment with the following command:

.. prompt:: bash

    pyenv virtualenv <name>

Replace ``<name>`` with whatever you like. If you ever forget what you named it,
you can always use the command ``pyenv versions`` to list all virtual environments.

Now activate your virtualenv with the following command:

.. prompt:: bash

    pyenv shell <name>

.. important::

    You must activate the virtual environment with the above command every time you open a new
    shell to run, install or update Red. You can check out other commands like ``pyenv local`` and
    ``pyenv global`` if you wish to keep the virtualenv activated all the time.
