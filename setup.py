import os
import sys
from setuptools import setup

if os.getenv("TOX_RED", False) and sys.version_info >= (3, 10):
    # We want to be able to test Python versions that we do not support yet.
    setup(python_requires=">=3.8.1")
else:
    # Metadata and options defined in setup.cfg
    setup()
