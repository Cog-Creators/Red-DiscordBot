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

Using a *single* virtual environment for all of your instances means you:

- Only need to update Red once for all instances.
- Must shut down all instances prior to updating.
- Will save space on your hard drive.

Using *multiple* virtual environments for each individual or select groups of instances means you:

- Need to update Red within each virtual environment separately.
- Can update Red without needing to update all instances.
- Only need to shut down the instance being updated.

.. important::

    Regardless of which option you choose, do not update the virtual environment while any
    instance is running. This is especially true for Windows as files are locked by the 
    system while in use.