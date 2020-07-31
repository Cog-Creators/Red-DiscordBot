from setuptools import setup
import os

if os.getenv("READTHEDOCS", False):
    setup(python_requires=">=3.7")
else:
    # Metadata and options defined in setup.cfg
    setup()
