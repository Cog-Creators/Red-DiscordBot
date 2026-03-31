# TODO list:
# - design ergonomic APIs instead of whatever you want to call what we have now
#     - try to be consistent about requiring Installable vs cog name
#       between cog install and other functionality
#     - use immutable objects more
#     - change Installable's equality to include its commit
#       (note: we currently heavily rely on this *not* being the case)
# - add asyncio.Lock appropriately for things that Downloader does
# - avoid doing some of the work on RepoManager initialization to speedup bot startup

from __future__ import annotations

import contextlib
import dataclasses
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import (
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
    TYPE_CHECKING,
)

import discord
from redbot.core import commands, Config, version_info as red_version_info
from redbot.core._cog_manager import CogManager
from redbot.core.data_manager import cog_data_path

from . import errors
from .log import log
from .installable import InstallableType, Installable, InstalledModule
from .repo_manager import RepoManager, Repo

if TYPE_CHECKING:
    from redbot.core.bot import Red


_SCHEMA_VERSION = 1
_config: Config
_bot_ref: Optional[Red]
_cog_mgr: CogManager
_repo_manager: RepoManager

LIB_PATH: Path
SHAREDLIB_PATH: Path
_SHAREDLIB_INIT: Path


async def _init(bot: Red) -> None:
    global _bot_ref
    _bot_ref = bot

    await _init_without_bot(_bot_ref._cog_mgr)


async def _init_without_bot(cog_manager: CogManager) -> None:
    global _cog_mgr
    _cog_mgr = cog_manager

    start = time.perf_counter()

    global _config
    _config = Config.get_conf(None, 998240343, cog_name="Downloader", force_registration=True)
    _config.register_global(schema_version=0, installed_cogs={}, installed_libraries={})
    await _migrate_config()

    global LIB_PATH, SHAREDLIB_PATH, _SHAREDLIB_INIT
    LIB_PATH = cog_data_path(raw_name="Downloader") / "lib"
    SHAREDLIB_PATH = LIB_PATH / "cog_shared"
    _SHAREDLIB_INIT = SHAREDLIB_PATH / "__init__.py"
    _create_lib_folder()

    global _repo_manager
    _repo_manager = RepoManager()
    await _repo_manager.initialize()

    stop = time.perf_counter()

    log.debug("Finished initialization in %.2fs", stop - start)


async def _migrate_config() -> None:
    schema_version = await _config.schema_version()

    if schema_version == _SCHEMA_VERSION:
        return

    if schema_version == 0:
        await _schema_0_to_1()
        schema_version += 1
        await _config.schema_version.set(schema_version)


async def _schema_0_to_1():
    """
    This contains migration to allow saving state
    of both installed cogs and shared libraries.
    """
    old_conf = await _config.get_raw("installed", default=[])
    if not old_conf:
        return
    async with _config.installed_cogs() as new_cog_conf:
        for cog_json in old_conf:
            repo_name = cog_json["repo_name"]
            module_name = cog_json["cog_name"]
            if repo_name not in new_cog_conf:
                new_cog_conf[repo_name] = {}
            new_cog_conf[repo_name][module_name] = {
                "repo_name": repo_name,
                "module_name": module_name,
                "commit": "",
                "pinned": False,
            }
    await _config.clear_raw("installed")
    # no reliable way to get installed libraries (i.a. missing repo name)
    # but it only helps `[p]cog update` run faster so it's not an issue


def _create_lib_folder(*, remove_first: bool = False) -> None:
    if remove_first:
        shutil.rmtree(str(LIB_PATH))
    SHAREDLIB_PATH.mkdir(parents=True, exist_ok=True)
    if not _SHAREDLIB_INIT.exists():
        with _SHAREDLIB_INIT.open(mode="w", encoding="utf-8") as _:
            pass


async def installed_cogs() -> Tuple[InstalledModule, ...]:
    """Get info on installed cogs.

    Returns
    -------
    `tuple` of `InstalledModule`
        All installed cogs.

    """
    installed = await _config.installed_cogs()
    # noinspection PyTypeChecker
    return tuple(
        InstalledModule.from_json(cog_json, _repo_manager)
        for repo_json in installed.values()
        for cog_json in repo_json.values()
    )


async def installed_libraries() -> Tuple[InstalledModule, ...]:
    """Get info on installed shared libraries.

    Returns
    -------
    `tuple` of `InstalledModule`
        All installed shared libraries.

    """
    installed = await _config.installed_libraries()
    # noinspection PyTypeChecker
    return tuple(
        InstalledModule.from_json(lib_json, _repo_manager)
        for repo_json in installed.values()
        for lib_json in repo_json.values()
    )


async def installed_modules() -> Tuple[InstalledModule, ...]:
    """Get info on installed cogs and shared libraries.

    Returns
    -------
    `tuple` of `InstalledModule`
        All installed cogs and shared libraries.

    """
    return await installed_cogs() + await installed_libraries()


async def _save_to_installed(modules: Iterable[InstalledModule]) -> None:
    """Mark modules as installed or updates their json in Config.

    Parameters
    ----------
    modules : `list` of `InstalledModule`
        The modules to check off.

    """
    async with _config.all() as global_data:
        installed_cogs = global_data["installed_cogs"]
        installed_libraries = global_data["installed_libraries"]
        for module in modules:
            if module.type is InstallableType.COG:
                installed = installed_cogs
            elif module.type is InstallableType.SHARED_LIBRARY:
                installed = installed_libraries
            else:
                continue
            module_json = module.to_json()
            repo_json = installed.setdefault(module.repo_name, {})
            repo_json[module.name] = module_json


async def _remove_from_installed(modules: Iterable[InstalledModule]) -> None:
    """Remove modules from the saved list
    of installed modules (corresponding to type of module).

    Parameters
    ----------
    modules : `list` of `InstalledModule`
        The modules to remove.

    """
    async with _config.all() as global_data:
        installed_cogs = global_data["installed_cogs"]
        installed_libraries = global_data["installed_libraries"]
        for module in modules:
            if module.type is InstallableType.COG:
                installed = installed_cogs
            elif module.type is InstallableType.SHARED_LIBRARY:
                installed = installed_libraries
            else:
                continue
            with contextlib.suppress(KeyError):
                installed[module._json_repo_name].pop(module.name)


async def _shared_lib_load_check(cog_name: str) -> Optional[Repo]:
    _is_installed, cog = await is_installed(cog_name)
    if _is_installed and cog.repo is not None and cog.repo.available_libraries:
        return cog.repo
    return None


async def is_installed(
    cog_name: str,
) -> Union[Tuple[Literal[True], InstalledModule], Tuple[Literal[False], None]]:
    """Check to see if a cog has been installed through Downloader.

    Parameters
    ----------
    cog_name : str
        The name of the cog to check for.

    Returns
    -------
    `tuple` of (`bool`, `InstalledModule`)
        :code:`(True, InstalledModule)` if the cog is installed, else
        :code:`(False, None)`.

    """
    for installed_cog in await installed_cogs():
        if installed_cog.name == cog_name:
            return True, installed_cog
    return False, None


async def _available_updates(
    cogs: Iterable[InstalledModule],
) -> Tuple[Tuple[Installable, ...], Tuple[Installable, ...]]:
    """
    Get cogs and libraries which can be updated.

    Parameters
    ----------
    cogs : `list` of `InstalledModule`
        List of cogs, which should be checked against the updates.

    Returns
    -------
    tuple
        2-tuple of cogs and libraries which can be updated.

    """
    repos = {cog.repo for cog in cogs if cog.repo is not None}
    _installed_libraries = await installed_libraries()

    modules: Set[InstalledModule] = set()
    cogs_to_update: Set[Installable] = set()
    libraries_to_update: Set[Installable] = set()
    # split libraries and cogs into 2 categories:
    # 1. `cogs_to_update`, `libraries_to_update` - module needs update, skip diffs
    # 2. `modules` - module MAY need update, check diffs
    for repo in repos:
        for lib in repo.available_libraries:
            try:
                index = _installed_libraries.index(lib)
            except ValueError:
                libraries_to_update.add(lib)
            else:
                modules.add(_installed_libraries[index])
    for cog in cogs:
        if cog.repo is None:
            # cog had its repo removed, can't check for updates
            continue
        if cog.commit:
            modules.add(cog)
            continue
        # marking cog for update if there's no commit data saved (back-compat, see GH-2571)
        last_cog_occurrence = await cog.repo.get_last_module_occurrence(cog.name)
        if last_cog_occurrence is not None and not last_cog_occurrence.disabled:
            cogs_to_update.add(last_cog_occurrence)

    # Reduces diff requests to a single dict with no repeats
    hashes: Dict[Tuple[Repo, str], Set[InstalledModule]] = defaultdict(set)
    for module in modules:
        module.repo = cast(Repo, module.repo)
        if module.repo.commit != module.commit:
            try:
                should_add = await module.repo.is_ancestor(module.commit, module.repo.commit)
            except errors.UnknownRevision:
                # marking module for update if the saved commit data is invalid
                last_module_occurrence = await module.repo.get_last_module_occurrence(module.name)
                if last_module_occurrence is not None and not last_module_occurrence.disabled:
                    if last_module_occurrence.type is InstallableType.COG:
                        cogs_to_update.add(last_module_occurrence)
                    elif last_module_occurrence.type is InstallableType.SHARED_LIBRARY:
                        libraries_to_update.add(last_module_occurrence)
            else:
                if should_add:
                    hashes[(module.repo, module.commit)].add(module)

    update_commits = []
    for (repo, old_hash), modules_to_check in hashes.items():
        modified = await repo.get_modified_modules(old_hash, repo.commit)
        for module in modules_to_check:
            try:
                index = modified.index(module)
            except ValueError:
                # module wasn't modified - we just need to update its commit
                module.commit = repo.commit
                update_commits.append(module)
            else:
                modified_module = modified[index]
                if modified_module.type is InstallableType.COG:
                    if not modified_module.disabled:
                        cogs_to_update.add(modified_module)
                elif modified_module.type is InstallableType.SHARED_LIBRARY:
                    libraries_to_update.add(modified_module)

    await _save_to_installed(update_commits)

    return (tuple(cogs_to_update), tuple(libraries_to_update))


async def _install_cogs(
    cogs: Iterable[Installable],
) -> Tuple[Tuple[InstalledModule, ...], Tuple[Installable, ...]]:
    """Installs a list of cogs.

    Parameters
    ----------
    cogs : `list` of `Installable`
        Cogs to install. ``repo`` property of those objects can't be `None`
    Returns
    -------
    tuple
        2-tuple of installed and failed cogs.
    """
    repos: Dict[str, Tuple[Repo, Dict[str, List[Installable]]]] = {}
    for cog in cogs:
        try:
            repo_by_commit = repos[cog.repo_name]
        except KeyError:
            cog.repo = cast(Repo, cog.repo)  # docstring specifies this already
            repo_by_commit = repos[cog.repo_name] = (cog.repo, defaultdict(list))
        cogs_by_commit = repo_by_commit[1]
        cogs_by_commit[cog.commit].append(cog)
    installed = []
    failed = []
    for repo, cogs_by_commit in repos.values():
        exit_to_commit = repo.commit
        for commit, cogs_to_install in cogs_by_commit.items():
            await repo.checkout(commit)
            for cog in cogs_to_install:
                if await cog.copy_to(await _cog_mgr.install_path()):
                    installed.append(InstalledModule.from_installable(cog))
                else:
                    failed.append(cog)
        await repo.checkout(exit_to_commit)

    # noinspection PyTypeChecker
    return (tuple(installed), tuple(failed))


async def _reinstall_libraries(
    libraries: Iterable[Installable],
) -> Tuple[Tuple[InstalledModule, ...], Tuple[Installable, ...]]:
    """Installs a list of shared libraries, used when updating.

    Parameters
    ----------
    libraries : `list` of `Installable`
        Libraries to reinstall. ``repo`` property of those objects can't be `None`
    Returns
    -------
    tuple
        2-tuple of installed and failed libraries.
    """
    repos: Dict[str, Tuple[Repo, Dict[str, Set[Installable]]]] = {}
    for lib in libraries:
        try:
            repo_by_commit = repos[lib.repo_name]
        except KeyError:
            lib.repo = cast(Repo, lib.repo)  # docstring specifies this already
            repo_by_commit = repos[lib.repo_name] = (lib.repo, defaultdict(set))
        libs_by_commit = repo_by_commit[1]
        libs_by_commit[lib.commit].add(lib)

    all_installed: List[InstalledModule] = []
    all_failed: List[Installable] = []
    for repo, libs_by_commit in repos.values():
        exit_to_commit = repo.commit
        for commit, libs in libs_by_commit.items():
            await repo.checkout(commit)
            installed, failed = await repo.install_libraries(
                target_dir=SHAREDLIB_PATH, req_target_dir=LIB_PATH, libraries=libs
            )
            all_installed += installed
            all_failed += failed
        await repo.checkout(exit_to_commit)

    # noinspection PyTypeChecker
    return (tuple(all_installed), tuple(all_failed))


async def _install_requirements(cogs: Iterable[Installable]) -> Tuple[str, ...]:
    """
    Installs requirements for given cogs.

    Parameters
    ----------
    cogs : `list` of `Installable`
        Cogs whose requirements should be installed.
    Returns
    -------
    tuple
        Tuple of failed requirements.
    """

    # Reduces requirements to a single list with no repeats
    requirements = {requirement for cog in cogs for requirement in cog.requirements}
    repos: List[Tuple[Repo, List[str]]] = [(repo, []) for repo in _repo_manager.repos]

    # This for loop distributes the requirements across all repos
    # which will allow us to concurrently install requirements
    for i, req in enumerate(requirements):
        repo_index = i % len(repos)
        repos[repo_index][1].append(req)

    has_reqs = list(filter(lambda item: len(item[1]) > 0, repos))

    failed_reqs = []
    for repo, reqs in has_reqs:
        for req in reqs:
            if not await repo.install_raw_requirements([req], LIB_PATH):
                failed_reqs.append(req)
    return tuple(failed_reqs)


async def _delete_cog(target: Path) -> None:
    """
    Removes an (installed) cog.
    :param target: Path pointing to an existing file or directory
    :return:
    """
    if not target.exists():
        return

    if target.is_dir():
        shutil.rmtree(str(target))
    elif target.is_file():
        os.remove(str(target))


async def _get_cogs_to_check(
    *,
    repos: Optional[Iterable[Repo]] = None,
    cogs: Optional[Iterable[InstalledModule]] = None,
    update_repos: bool = True,
) -> Tuple[Set[InstalledModule], List[str]]:
    failed = []
    if not (cogs or repos):
        if update_repos:
            __, failed = await _repo_manager.update_repos()

        cogs_to_check = {
            cog
            for cog in await installed_cogs()
            if cog.repo is not None and cog.repo.name not in failed
        }
    else:
        # this is enough to be sure that `cogs` is not None (based on if above)
        if not repos:
            cogs = cast(Iterable[InstalledModule], cogs)
            repos = {cog.repo for cog in cogs if cog.repo is not None}

        if update_repos:
            __, failed = await _repo_manager.update_repos(repos)

        if failed:
            # remove failed repos
            repos = {repo for repo in repos if repo.name not in failed}

        if cogs:
            cogs_to_check = {cog for cog in cogs if cog.repo is not None and cog.repo in repos}
        else:
            cogs_to_check = {
                cog for cog in await installed_cogs() if cog.repo is not None and cog.repo in repos
            }

    return (cogs_to_check, failed)


# functionality extracted from command implementations
# TODO: make them into nice APIs instead of what they are now...


async def pip_install(*deps: str) -> bool:
    repo = Repo("", "", "", "", Path.cwd())
    return await repo.install_raw_requirements(deps, LIB_PATH)


async def reinstall_requirements() -> tuple[List[str], List[str]]:
    _create_lib_folder(remove_first=True)
    _installed_cogs = await installed_cogs()
    cogs = []
    repos = set()
    for cog in _installed_cogs:
        if cog.repo is None:
            continue
        repos.add(cog.repo)
        cogs.append(cog)
    failed_reqs = await _install_requirements(cogs)
    all_installed_libs: List[InstalledModule] = []
    all_failed_libs: List[Installable] = []
    for repo in repos:
        installed_libs, failed_libs = await repo.install_libraries(
            target_dir=SHAREDLIB_PATH, req_target_dir=LIB_PATH
        )
        all_installed_libs += installed_libs
        all_failed_libs += failed_libs

    return failed_reqs, all_failed_libs


async def install_cogs(
    repo: Repo, rev: Optional[str], cog_names: Iterable[str]
) -> CogInstallResult:
    commit = None

    if rev is not None:
        # raises errors.AmbiguousRevision and errors.UnknownRevision
        commit = await repo.get_full_sha1(rev)

    cog_names = set(cog_names)
    _installed_cogs = await installed_cogs()

    cogs: List[Installable] = []
    unavailable_cogs: List[str] = []
    already_installed: List[Installable] = []
    name_already_used: List[Installable] = []
    incompatible_python_version: List[Installable] = []
    incompatible_bot_version: List[Installable] = []

    result_installed_cogs: Tuple[InstalledModule, ...] = ()
    result_failed_cogs: Tuple[Installable, ...] = ()
    result_failed_reqs: Tuple[str, ...] = ()
    result_installed_libs: Tuple[InstalledModule, ...] = ()
    result_failed_libs: Tuple[Installable, ...] = ()

    async with repo.checkout(commit, exit_to_rev=repo.branch):
        for cog_name in cog_names:
            cog: Optional[Installable] = discord.utils.get(repo.available_cogs, name=cog_name)
            if cog is None:
                unavailable_cogs.append(cog_name)
            elif cog in _installed_cogs:
                already_installed.append(cog)
            elif discord.utils.get(_installed_cogs, name=cog.name):
                name_already_used.append(cog)
            elif cog.min_python_version > sys.version_info:
                incompatible_python_version.append(cog)
            elif cog.min_bot_version > red_version_info or (
                # max version should be ignored when it's lower than min version
                cog.min_bot_version <= cog.max_bot_version
                and cog.max_bot_version < red_version_info
            ):
                incompatible_bot_version.append(cog)
            else:
                cogs.append(cog)

        if cogs:
            result_failed_reqs = await _install_requirements(cogs)
            if not result_failed_reqs:
                result_installed_cogs, result_failed_cogs = await _install_cogs(cogs)

    if cogs and not result_failed_reqs:
        result_installed_libs, result_failed_libs = await repo.install_libraries(
            target_dir=SHAREDLIB_PATH, req_target_dir=LIB_PATH
        )
        if rev is not None:
            for cog in result_installed_cogs:
                cog.pinned = True
        await _save_to_installed(result_installed_cogs + result_installed_libs)

    return CogInstallResult(
        installed_cogs=result_installed_cogs,
        installed_libs=result_installed_libs,
        failed_cogs=result_failed_cogs,
        failed_libs=result_failed_libs,
        failed_reqs=result_failed_reqs,
        unavailable_cogs=tuple(unavailable_cogs),
        already_installed=tuple(already_installed),
        name_already_used=tuple(name_already_used),
        incompatible_python_version=tuple(incompatible_python_version),
        incompatible_bot_version=tuple(incompatible_bot_version),
    )


async def uninstall_cogs(*cogs: InstalledModule) -> tuple[list[str], list[str]]:
    uninstalled_cogs = []
    failed_cogs = []
    for cog in set(cogs):
        real_name = cog.name

        poss_installed_path = (await _cog_mgr.install_path()) / real_name
        if poss_installed_path.exists():
            if _bot_ref is not None:
                with contextlib.suppress(commands.ExtensionNotLoaded):
                    await _bot_ref.unload_extension(real_name)
                    await _bot_ref.remove_loaded_package(real_name)
            await _delete_cog(poss_installed_path)
            uninstalled_cogs.append(real_name)
        else:
            failed_cogs.append(real_name)
    await _remove_from_installed(cogs)

    return uninstalled_cogs, failed_cogs


async def check_cog_updates(
    *,
    repos: Optional[Iterable[Repo]] = None,
    cogs: Optional[Iterable[InstalledModule]] = None,
    update_repos: bool = True,
) -> CogUpdateCheckResult:
    cogs_to_check, failed_repos = await _get_cogs_to_check(
        repos=repos, cogs=cogs, update_repos=update_repos
    )
    outdated_cogs, outdated_libs = await _available_updates(cogs_to_check)

    updatable_cogs: List[Installable] = []
    incompatible_python_version: List[Installable] = []
    incompatible_bot_version: List[Installable] = []
    for cog in outdated_cogs:
        if cog.min_python_version > sys.version_info:
            incompatible_python_version.append(cog)
        elif cog.min_bot_version > red_version_info or (
            # max version should be ignored when it's lower than min version
            cog.min_bot_version <= cog.max_bot_version
            and cog.max_bot_version < red_version_info
        ):
            incompatible_bot_version.append(cog)
        else:
            updatable_cogs.append(cog)

    return CogUpdateCheckResult(
        outdated_cogs=outdated_cogs,
        outdated_libs=outdated_libs,
        updatable_cogs=tuple(updatable_cogs),
        failed_repos=tuple(failed_repos),
        incompatible_python_version=tuple(incompatible_python_version),
        incompatible_bot_version=tuple(incompatible_bot_version),
    )


# update given cogs or all cogs
async def update_cogs(
    *, cogs: Optional[List[InstalledModule]] = None, repos: Optional[List[Repo]] = None
) -> CogUpdateResult:
    if cogs is not None and repos is not None:
        raise ValueError("You can specify cogs or repos argument, not both")

    cogs_to_check, failed_repos = await _get_cogs_to_check(repos=repos, cogs=cogs)
    return await _update_cogs(cogs_to_check, failed_repos=failed_repos)


# update given cogs or all cogs from the specified repo
# using the specified revision (or latest if not specified)
async def update_repo_cogs(
    repo: Repo, cogs: Optional[List[InstalledModule]] = None, *, rev: Optional[str] = None
) -> CogUpdateResult:
    try:
        await repo.update()
    except errors.UpdateError:
        return await _update_cogs(set(), failed_repos=[repo])

    # TODO: should this be set to `repo.branch` when `rev` is None?
    commit = None
    if rev is not None:
        # raises errors.AmbiguousRevision and errors.UnknownRevision
        commit = await repo.get_full_sha1(rev)
    async with repo.checkout(commit, exit_to_rev=repo.branch):
        cogs_to_check, __ = await _get_cogs_to_check(repos=[repo], cogs=cogs, update_repos=False)
        return await _update_cogs(cogs_to_check, failed_repos=())


async def _update_cogs(
    cogs_to_check: Set[InstalledModule], *, failed_repos: Sequence[Repo]
) -> CogUpdateResult:
    pinned_cogs = {cog for cog in cogs_to_check if cog.pinned}
    cogs_to_check -= pinned_cogs

    outdated_cogs: Tuple[Installable, ...] = ()
    outdated_libs: Tuple[Installable, ...] = ()
    updatable_cogs: List[Installable] = []
    incompatible_python_version: List[Installable] = []
    incompatible_bot_version: List[Installable] = []

    updated_cogs: Tuple[InstalledModule, ...] = ()
    failed_cogs: Tuple[Installable, ...] = ()
    failed_reqs: Tuple[str, ...] = ()
    updated_libs: Tuple[InstalledModule, ...] = ()
    failed_libs: Tuple[Installable, ...] = ()

    if cogs_to_check:
        outdated_cogs, outdated_libs = await _available_updates(cogs_to_check)

        for cog in outdated_cogs:
            if cog.min_python_version > sys.version_info:
                incompatible_python_version.append(cog)
            elif cog.min_bot_version > red_version_info or (
                # max version should be ignored when it's lower than min version
                cog.min_bot_version <= cog.max_bot_version
                and cog.max_bot_version < red_version_info
            ):
                incompatible_bot_version.append(cog)
            else:
                updatable_cogs.append(cog)

        if updatable_cogs or outdated_libs:
            failed_reqs = await _install_requirements(updatable_cogs)
            if not failed_reqs:
                updated_cogs, failed_cogs = await _install_cogs(updatable_cogs)
                updated_libs, failed_libs = await _reinstall_libraries(outdated_libs)
                await _save_to_installed(updated_cogs + updated_libs)

    return CogUpdateResult(
        checked_cogs=frozenset(cogs_to_check),
        pinned_cogs=frozenset(pinned_cogs),
        updated_cogs=updated_cogs,
        updated_libs=updated_libs,
        failed_cogs=failed_cogs,
        failed_libs=failed_libs,
        failed_reqs=failed_reqs,
        outdated_cogs=outdated_cogs,
        outdated_libs=outdated_libs,
        updatable_cogs=tuple(updatable_cogs),
        failed_repos=tuple(failed_repos),
        incompatible_python_version=tuple(incompatible_python_version),
        incompatible_bot_version=tuple(incompatible_bot_version),
    )


async def pin_cogs(
    *cogs: InstalledModule,
) -> tuple[tuple[InstalledModule, ...], tuple[InstalledModule, ...]]:
    already_pinned = []
    pinned = []
    for cog in set(cogs):
        if cog.pinned:
            already_pinned.append(cog)
            continue
        cog.pinned = True
        pinned.append(cog)
    if pinned:
        await _save_to_installed(pinned)

    return tuple(pinned), tuple(already_pinned)


async def unpin_cogs(
    *cogs: InstalledModule,
) -> tuple[tuple[InstalledModule, ...], tuple[InstalledModule, ...]]:
    not_pinned = []
    unpinned = []
    for cog in set(cogs):
        if not cog.pinned:
            not_pinned.append(cog)
            continue
        cog.pinned = False
        unpinned.append(cog)
    if unpinned:
        await _save_to_installed(unpinned)

    return tuple(unpinned), tuple(not_pinned)


# TODO: make kw_only
@dataclasses.dataclass
class CogInstallResult:
    installed_cogs: Tuple[InstalledModule, ...]
    installed_libs: Tuple[InstalledModule, ...]
    failed_cogs: Tuple[Installable, ...]
    failed_libs: Tuple[Installable, ...]
    failed_reqs: Tuple[str, ...]
    unavailable_cogs: Tuple[str, ...]
    already_installed: Tuple[Installable, ...]
    name_already_used: Tuple[Installable, ...]
    incompatible_python_version: Tuple[Installable, ...]
    incompatible_bot_version: Tuple[Installable, ...]


# TODO: make kw_only
@dataclasses.dataclass
class CogUpdateCheckResult:
    outdated_cogs: Tuple[Installable, ...]
    outdated_libs: Tuple[Installable, ...]
    updatable_cogs: Tuple[Installable, ...]
    failed_repos: Tuple[Repo, ...]
    incompatible_python_version: Tuple[Installable, ...]
    incompatible_bot_version: Tuple[Installable, ...]

    @property
    def updates_available(self) -> bool:
        return bool(self.outdated_cogs or self.outdated_libs)

    @property
    def updates_installable(self) -> bool:
        return bool(self.updatable_cogs or self.outdated_libs)

    @property
    def incompatible_cogs(self) -> Tuple[Installable, ...]:
        return self.incompatible_python_version + self.incompatible_bot_version


# TODO: make kw_only
@dataclasses.dataclass
class CogUpdateResult(CogUpdateCheckResult):
    # checked_cogs contains old modules, before update
    checked_cogs: Set[InstalledModule]
    pinned_cogs: Set[InstalledModule]
    updated_cogs: Tuple[InstalledModule, ...]
    updated_libs: Tuple[InstalledModule, ...]
    failed_cogs: Tuple[Installable, ...]
    failed_libs: Tuple[Installable, ...]
    failed_reqs: Tuple[str, ...]

    @property
    def updated_modules(self) -> Tuple[InstalledModule, ...]:
        return self.updated_cogs + self.updated_libs


class CogUnavailableError(Exception):
    def __init__(self, repo_name: str, cog_name: str) -> None:
        self.repo_name = repo_name
        self.cog_name = cog_name
        super().__init__(f"Couldn't find cog {cog_name!r} in {repo_name!r}")
