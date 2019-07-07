import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


class RepoJSONMixin:
    INFO_FILE_NAME = "info.json"

    def __init__(self, repo_folder: Path):
        self._repo_folder = repo_folder

        self.author: Optional[Tuple[str, ...]] = None
        self.install_msg: Optional[str] = None
        self.short: Optional[str] = None
        self.description: Optional[str] = None

        self._info_file = repo_folder / self.INFO_FILE_NAME
        if self._info_file.exists():
            self._read_info_file()

        self._info: Dict[str, Any] = {}

    def _read_info_file(self) -> None:
        if not (self._info_file.exists() or self._info_file.is_file()):
            return

        try:
            with self._info_file.open(encoding="utf-8") as f:
                info = json.load(f)
        except json.JSONDecodeError:
            return
        else:
            self._info = info

        self.author = info.get("author")
        self.install_msg = info.get("install_msg")
        self.short = info.get("short")
        self.description = info.get("description")
