"""Integration test ensuring `redbot --dry-run` exits cleanly."""

from __future__ import annotations

import subprocess
import sys


def test_dry_run_exits_cleanly():
    """Running `redbot --dry-run` should exit with code 0 and without AttributeError."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "redbot",
            "--no-instance",
            "--dry-run",
            "--no-prompt",
            "--token",
            "dummy_token_for_testing",
            "--prefix",
            "!",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        "Expected redbot dry-run to exit with code 0, "
        f"got {result.returncode}.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "AttributeError" not in result.stderr, (
        "redbot dry-run emitted AttributeError on stderr, indicating shutdown guard failed.\n"
        f"STDERR:\n{result.stderr}"
    )
