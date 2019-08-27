import json
import os
import tarfile
from pathlib import Path
from typing import Optional
from datetime import datetime

from .. import data_manager
from .chat_formatting import box
from .fuzzy import *
from .tasks import *
from .utils import *


async def create_backup(dest: Path = Path.home()) -> Optional[Path]:
    data_path = Path(data_manager.core_data_path().parent)
    if not data_path.exists():
        return

    dest.mkdir(parents=True, exist_ok=True)
    timestr = datetime.utcnow().isoformat(timespec="minutes")
    backup_fpath = dest / f"redv3_{data_manager.instance_name}_{timestr}.tar.gz"

    to_backup = []
    exclusions = [
        "__pycache__",
        "Lavalink.jar",
        os.path.join("Downloader", "lib"),
        os.path.join("CogManager", "cogs"),
        os.path.join("RepoManager", "repos"),
    ]

    # Avoiding circular imports
    from ...cogs.downloader.repo_manager import RepoManager

    repo_mgr = RepoManager()
    await repo_mgr.initialize()
    repo_output = []
    for _, repo in repo_mgr._repos:
        repo_output.append({"url": repo.url, "name": repo.name, "branch": repo.branch})
    repos_file = data_path / "cogs" / "RepoManager" / "repos.json"
    with repos_file.open("w") as fs:
        json.dump(repo_output, fs, indent=4)
    instance_file = data_path / "instance.json"
    with instance_file.open("w") as fs:
        json.dump({data_manager.instance_name: data_manager.basic_config}, fs, indent=4)
    for f in data_path.glob("**/*"):
        if not any(ex in str(f) for ex in exclusions) and f.is_file():
            to_backup.append(f)

    with tarfile.open(str(backup_fpath), "w:gz") as tar:
        for f in to_backup:
            tar.add(str(f), arcname=f.relative_to(data_path), recursive=False)
    return backup_fpath
