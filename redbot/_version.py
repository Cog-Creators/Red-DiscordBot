def _get_version(*, ignore_installed: bool = False) -> str:
    if not __version__.endswith(".dev1"):
        return __version__
    try:
        import os
        import subprocess

        path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        output = subprocess.check_output(
            ("git", "describe", "--tags", "--long", "--dirty"), cwd=path
        )
        _, count, commit, *dirty = output.decode("utf-8").strip().split("-", 3)
        dirty_suffix = f".{dirty[0]}" if dirty else ""
        return f"{__version__[:-1]}{count}+{commit}{dirty_suffix}"
    except Exception:
        # `ignore_installed` is `True` when building with setuptools.
        if ignore_installed:
            # we don't want any failure to raise here but we should print it
            import traceback

            traceback.print_exc()
        else:
            try:
                from importlib.metadata import version

                return version("Red-DiscordBot")
            except Exception:
                # we don't want any failure to raise here but we should print it
                import traceback

                traceback.print_exc()

    return __version__


__version__ = "3.5.0.dev1"
