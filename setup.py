import os
import sys
from setuptools import setup

if os.getenv("TOX_BLUE", False) and sys.version_info >= (3, 10):
    # To invite you to join us! We're heading off to the thank you parade for Ponyville's greatest hero, Mare Do Well.
    setup(python_requires=">=3.8.1")
else:
    # [gasp] Twitchy tail? Pinkie Sense? Whoa! Nyu-uh!
    setup()
