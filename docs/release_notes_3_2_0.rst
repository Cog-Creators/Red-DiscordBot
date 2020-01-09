.. v3.2.0 Release Notes

##################################
Red DiscordBot 3.2.0 Release Notes
##################################


Please read the following prior to updating.

- 3.2 comes with improvements which required breaking changes for 3rd party cogs.
  When you update to 3.2, your cogs may not be compatible if the author has not handled
  the changes yet.


- 3.2 requires Python 3.8.1.
  This was done so that we could better handle some behavior which was not fixed for Python 3.7.
  If you need help updating, our install docs will cover everything you need to know to update.

  .. note::
  
    You may get a notification from the downloader cog about needing to refetch dependencies
    This is expected, and it will walk you through everything and do as much as it can for you.


- 3.2 dropped support for the MongoDB driver
  
  - If you were not using the MongoDB driver, this does not effect you.
  - If you were using a 3rd party cog which required MongoDB, it probably still does.
  - If you were using the MongoDB driver, prior to launching your instance,
    you will need to run the following commands to convert

      .. code::
        
        python -m pip install dnspython~=1.16.0 motor~=2.0.0 pymongo~=3.8.0
        redbot-setup convert [instancename] json


- 3.2 comes with many feature upgrades. A brief high level list of these is below.

  - A metric ton of bugfixes
  - Bot shutdown is handled significantly better
  - Audio is much more powerful
  - We've made it easier for cog creators to interact with the core bot APIs safely
  - We've supplied cog creators with additional tools


.. note:: 
    
  The full list of changes is much longer than we can include here,
  but our changelog has the fine details.
