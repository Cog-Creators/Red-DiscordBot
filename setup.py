import os
import sys
from setuptools import find_namespace_packages, setup

# Since we're importing `redbot` package, we have to ensure that it's in sys.path.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from redbot import VersionInfo

version, _ = VersionInfo._get_version(ignore_installed=True)

python_requires = ">=3.8.1"
if not os.getenv("TOX_RED", False) or sys.version_info < (3, 10):
    python_requires += ",<3.10"

# Metadata and options defined in pyproject.toml
setup(
    version=version,
    python_requires=python_requires,
    # TODO: use [project] table once PEP 639 gets accepted
    license_files=["LICENSE", "redbot/**/*.LICENSE"],
    # TODO: use [tool.setuptools.packages] table once this feature gets out of beta
    packages=find_namespace_packages(include=["redbot", "redbot.*"]),
)
