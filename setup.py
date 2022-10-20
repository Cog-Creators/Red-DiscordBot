import os
import sys
from setuptools import setup

# Since we're importing `redbot` package, we have to ensure that it's in sys.path.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from redbot import VersionInfo

version, _ = VersionInfo._get_version(ignore_installed=True)

if os.getenv("TOX_RED", False) and sys.version_info >= (3, 10):
    # We want to be able to test Python versions that we do not support yet.
    setup(python_requires=">=3.8.1", version=version)
else:
    # Metadata and options defined in setup.cfg
    setup(version=version)
