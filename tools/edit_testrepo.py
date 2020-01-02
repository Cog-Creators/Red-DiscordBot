#!/usr/bin/env python3.8
"""Script to edit test repo used by Downloader git integration tests.

This script aims to help update the human-readable version of repo
used for git integration tests in ``redbot/tests/downloader_testrepo.export``
by exporting/importing it in/from provided directory.

What this script does
---------------------
edit_testrepo.py import:
    It inits test repo in provided directory, sets up committer data in git config,
    imports the repo from ``redbot/tests/downloader_testrepo.export`` using
    git's fast-import command and updates repo's working tree.
edit_testrepo.py export:
    It exports repo from provided directory into ``redbot/tests/downloader_testrepo.export``
    using git's fast-export. To make the file more useful for developers,
    it's called with option that adds extra directive ``original-oid <SHA1SUM>``,
    which while ignored by import, might ease up creating tests without importing the repo.

Note
----
Editing `downloader_git_test_repo.export` file manually is strongly discouraged,
especially editing any part of commit directives as that causes a change in the commit's hash.
Another problem devs could encounter when trying to manually edit that file
are editors that will use CRLF instead of LF for new line character(s) and therefore break it.

Also, if Git ever changes currently used SHA-1 to SHA-256 we will have to
update old hashes with new ones. But it's a small drawback,
when we can have human-readable version of repo.

Known limitations
-----------------
``git fast-export`` exports commits without GPG signs so this script disables it in repo's config.
This also means devs shouldn't use ``--gpg-sign`` flag in ``git commit`` within the test repo.
"""
import shlex
import subprocess as sp
from pathlib import Path
from typing import Tuple

import click


MAIN_DIRECTORY = Path(__file__).absolute().parent.parent
TEST_REPO_EXPORT_PTH: Path = MAIN_DIRECTORY / "redbot" / "pytest" / "downloader_testrepo.export"


class ClickCustomPath(click.Path):
    """Similar to `click.Path` but returns `Path` object instead."""

    def convert(self, value, param, ctx):
        path_string = super().convert(value, param, ctx)
        return Path(path_string)


class EmptyDirectory(ClickCustomPath):
    """Similar to `ClickCustomPath`, but only allows empty or non-existent directories.
    Unlike `ClickCustomPath`, this type doesn't accept
    'file_okay', 'dir_okay' and 'readable' keyword arguments.
    """

    def __init__(self, **kwargs):
        super().__init__(readable=True, dir_okay=True, file_okay=False, **kwargs)

    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)
        if path.exists() and next(path.glob("*"), None) is not None:
            self.fail(f'Directory "{str(path)}" is not empty!')
        return path


class GitRepoDirectory(ClickCustomPath):
    """Similar to `ClickCustomPath`, but only allows git repo directories.
    Unlike `ClickCustomPath`, this type doesn't accept
    'file_okay', 'dir_okay' and 'readable' keyword arguments.
    """

    def __init__(self, **kwargs):
        super().__init__(readable=True, dir_okay=True, file_okay=False, **kwargs)

    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)
        git_path = path / ".git"
        if not git_path.exists():
            self.fail(f"A git repo does not exist at path: {str(path)}")
        return path


@click.group()
def cli():
    """Downloader test repo commands."""


@cli.command(name="init", short_help="Init a new test repo in chosen directory.")
@click.argument("destination", type=EmptyDirectory(writable=True, resolve_path=True))
def git_init(destination: Path):
    """Init a new test repo in chosen directory. This might be useful
    if someone will ever want to make a completely new test repo without importing it."""
    init_test_repo(destination)
    click.echo(f'New test repo successfully initialized at "{str(destination)}".')


@cli.command(name="import", short_help="Import test repo into chosen directory.")
@click.argument("destination", type=EmptyDirectory(writable=True, resolve_path=True))
def git_import(destination: Path):
    """Import test repo into chosen directory."""
    if not TEST_REPO_EXPORT_PTH.is_file():
        raise click.ClickException(f'File "{str(TEST_REPO_EXPORT_PTH)}" can\'t be found.')
    git_dirparams = init_test_repo(destination)

    fast_import = sp.Popen((*git_dirparams, "fast-import", "--quiet"), stdin=sp.PIPE)
    with TEST_REPO_EXPORT_PTH.open(mode="rb") as f:
        fast_import.communicate(f.read())
    return_code = fast_import.wait()
    if return_code:
        raise click.ClickException(f"git fast-import failed with code {return_code}")

    _run((*git_dirparams, "reset", "--hard"))
    click.echo(
        f'Test repo successfully imported at "{str(destination)}"\n'
        'When you\'ll update it, use "edit_testrepo.py export" to update test repo file.'
    )


@cli.command(name="export", short_help="Export repo to test repo file.")
@click.argument("source", type=GitRepoDirectory(resolve_path=True))
@click.option("--yes", is_flag=True)
def git_export(source: Path, yes: bool):
    if not yes and TEST_REPO_EXPORT_PTH.is_file():
        click.confirm(
            f"Test repo file ({str(TEST_REPO_EXPORT_PTH)}) already exists, "
            "are you sure you want to replace it?",
            abort=True,
        )
    p = _run(
        ("git", "-C", str(source), "fast-export", "--all", "--show-original-ids"), stdout=sp.PIPE
    )
    with TEST_REPO_EXPORT_PTH.open(mode="wb") as f:
        f.write(
            b"# THIS FILE SHOULDN'T BE EDITED MANUALLY. "
            b"USE `edit_testrepo.py` TOOL TO UPDATE THE REPO.\n" + p.stdout
        )
    click.echo("Test repo successfully exported.")


def init_test_repo(destination: Path):
    destination.mkdir(exist_ok=True)
    git_dirparams = ("git", "-C", str(destination))
    init_commands: Tuple[Tuple[str, ...], ...] = (
        (*git_dirparams, "init"),
        (*git_dirparams, "config", "--local", "user.name", "Cog-Creators"),
        (*git_dirparams, "config", "--local", "user.email", "cog-creators@example.org"),
        (*git_dirparams, "config", "--local", "commit.gpgSign", "false"),
    )

    for args in init_commands:
        _run(args)
    return git_dirparams


def _run(args, stderr=None, stdout=sp.DEVNULL) -> sp.CompletedProcess:
    try:
        return sp.run(args, stderr=stderr, stdout=stdout, check=True)
    except sp.CalledProcessError as exc:
        cmd = " ".join(map(lambda c: shlex.quote(str(c)), exc.cmd))
        raise click.ClickException(
            f"The following command failed with code {exc.returncode}:\n    {cmd}"
        )


if __name__ == "__main__":
    cli()
