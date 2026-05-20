# This is a compatibility shim for people using Downloader internal pre-3.5.25.
# It will probably get removed in Red 3.6.

# import everything from repo_manager module
from redbot.core._downloader.repo_manager import *

# use Repo subclass with `convert()` method instead of Repo from repo_manager module
from .converters import Repo
