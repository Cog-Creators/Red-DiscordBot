.. _about-venvs:

==========================
About Virtual Environments
==========================
Creating a virtual environment is simple and helps prevent installation problems.

**What Are Virtual Environments For?**

Virtual environments allow you to isolate Red's library dependencies, cog dependencies and python
binaries from the rest of your system with no performance overhead.
It also ensures Red and its dependencies are installed to a predictable location, which makes 
uninstalling Red as simple as removing a single folder. Preventing any loss of data 
or breaking other things on your system.


--------------------------------------------
Virtual Environments with Multiple Instances
--------------------------------------------
If you are running multiple instances of Red on the same machine, you have the option of either
using the same virtual environment for all of them, or creating separate ones.

The advantages of using a *single* virtual environment for all of your instances are:

- When updating Red, you only need to update it once for all instances.
    - However, you must shut down all instances before updating.
- It will save space on your hard drive.

The advantages of using *multiple* virtual environments for all of your instances are:

- You can update each of your instances individually.
- Only the instances in the venv need to be shut down prior to updating.

.. important::

    Regardless of which option you choose, do not update the virtual environment while any
    instance is running. This is especially true for Windows as files are locked by the 
    system while in use.