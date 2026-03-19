.. _about-venvs:

==========================
About Virtual Environments
==========================
Creating a virtual environment is simple and helps prevent installation problems.

**What Are Virtual Environments For?**

Virtual environments allow you to isolate Red's library dependencies, cog dependencies, and Python
binaries from the rest of your system with no performance overhead, ensuring those dependencies 
and Red are installed to a predictable location. This makes uninstalling Red as simple as removing 
a single folder, preventing any data loss or breaking other things on your system.


--------------------------------------------
Virtual Environments with Multiple Instances
--------------------------------------------
If you are running multiple instances of Red on the same machine, you have the option of either
using the same virtual environment for all of them, or creating separate ones.

Using a *single* virtual environment for all of your instances means you:

- Only need to update Red once for all instances.
- Must shut down all instances prior to updating.
- Will save space on your hard drive.
- Want all instances to share the same version/dependencies.

Using *multiple* virtual environments for each individual or select groups of instances means you:

- Need to update Red within each virtual environment separately.
- Can update Red without needing to update all instances.
- Only need to shut down the instance(s) being updated.
- Want different Red/dependency versions on different instances.

.. important::

    Regardless of which option you choose, do not update while any instances within that virtual 
    environment are running. This is especially true for Windows, as files are locked by the system while in use.