.. _about-venvs:

==========================
About Virtual Environments
==========================
Creating a virtual environment is really easy and usually prevents many common installation
problems.

**What Are Virtual Environments For?**

Virtual environments allow you to isolate Red's library dependencies, cog dependencies and python
binaries from the rest of your system. There is no performance overhead to using virtual environment
and it saves you from a lot of troubles during setup. It also makes sure Red and its dependencies
are installed to a predictable location which makes uninstalling Red as simple as removing a single folder,
without worrying about losing your data or other things on your system becoming broken.


--------------------------------------------
Virtual Environments with Multiple Instances
--------------------------------------------
If you are running multiple instances of Red on the same machine, you have the option of either
using the same virtual environment for all of them, or creating separate ones.

.. note::

    This only applies for multiple instances of V3. If you are running a V2 instance as well,
    you **must** use separate virtual environments.

The advantages of using a *single* virtual environment for all of your V3 instances are:

- When updating Red, you will only need to update it once for all instances (however you will still need to restart all instances for the changes to take effect)
- It will save space on your hard drive

On the other hand, you may wish to update each of your instances individually.

.. important::

    Windows users with multiple instances should create *separate* virtual environments, as
    updating multiple running instances at once is likely to cause errors.
