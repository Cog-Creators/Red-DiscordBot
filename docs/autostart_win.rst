.. windows service guide

==================================
Setting up auto-restart on Windows
==================================

-------------------------------
Downloading NSSM via Chocolatey
-------------------------------

.. note:: This assumes you already have chocolatey installed. 
          If not, you may install it or follow the manual instructions for getting NSSM

To install via Chocolatey, search "powershell" in the windows start menu,
right-click on it and then click "Run as administrator"

Then run the following command:

.. code-block:: none

    choco install nssm -y