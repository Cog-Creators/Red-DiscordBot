from pathlib import Path

from core.drivers.red_json import JSON as JSONDriver
from core.drivers.red_mongo import Mongo
import logging

from typing import Callable

log = logging.getLogger("red.config")

