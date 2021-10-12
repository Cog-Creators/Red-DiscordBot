------------------------------
Creating a Virtual Environment
------------------------------

.. tip::

    If you want to learn more about virtual environments, see page: `about-venvs`

We require installing Red into a virtual environment. Don't be scared, it's very
straightforward.

**************
Using ``venv``
**************

This is the quickest way to get your virtual environment up and running, as `venv` is shipped with
python.

First, choose a directory where you would like to create your virtual environment. It's a good idea
to keep it in a location which is easy to type out the path to. From now, we'll call it
``redenv`` and it will be located in your home directory.

Create your virtual environment with the following command:

.. prompt:: bash

    python3.9 -m venv ~/redenv

And activate it with the following command:

.. prompt:: bash

    source ~/redenv/bin/activate

.. important::

    You must activate the virtual environment with the above command every time you open a new
    shell to run, install or update Red.
