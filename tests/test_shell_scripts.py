"""Regression tests for the bash helpers.

These run offline: the slackdump binary is replaced by a stub that records
its command line arguments, so we can assert how credentials are handed over.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform == "win32", reason="bash helper scripts")
def test_workspace_setup_passes_secrets_via_environment_not_argv(tmp_path: Path):
    """`ensure_workspace` must not expose the token on the command line."""
    argv_log = tmp_path / "argv.txt"
    env_log = tmp_path / "env.txt"

    stub = tmp_path / "slackdump"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf \'%s\\n\' "$@" > "{argv_log}"\n'
        f'printf \'%s\\n\' "${{SLACK_TOKEN:-unset}}" "${{SLACK_COOKIE:-unset}}" '
        f'> "{env_log}"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    # Point REPO_ROOT at an empty directory so a real .env next to the
    # repository cannot leak into (or override) the test credentials.
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()

    script = f"""
    set -euo pipefail
    source "{REPO_ROOT}/scripts/lib.sh"
    REPO_ROOT="{fake_repo}"
    SLACKDUMP_BIN="{stub}"
    SLACK_TOKEN="xoxc-test-token"
    COOKIE="xoxd-test-cookie"
    export SLACK_TOKEN COOKIE
    ensure_workspace
    """
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env={
            "HOME": str(fake_home),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        },
    )

    assert result.returncode == 0, result.stderr
    assert argv_log.exists(), "ensure_workspace did not invoke slackdump"

    argv = argv_log.read_text(encoding="utf-8").splitlines()
    assert argv == ["workspace", "new", "-load-env", "default"]

    secrets = ("xoxc-test-token", "xoxd-test-cookie")
    assert not any(secret in line for secret in secrets for line in argv)

    token, cookie = env_log.read_text(encoding="utf-8").splitlines()
    # exported for slackdump's -load-env, and COOKIE accepted as the alias
    assert token == "xoxc-test-token"
    assert cookie == "xoxd-test-cookie"


@pytest.mark.skipif(sys.platform == "win32", reason="bash helper scripts")
def test_check_auth_vars_rejects_missing_credentials(tmp_path: Path):
    script = f"""
    set -euo pipefail
    source "{REPO_ROOT}/scripts/lib.sh"
    REPO_ROOT="{tmp_path}"
    check_auth_vars
    """
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env={"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )

    assert result.returncode == 1
    assert "SLACK_TOKEN is not set" in result.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="bash helper scripts")
def test_find_export_file_prefers_channel_file_and_falls_back(tmp_path: Path):
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    fallback_file = export_dir / "other.json"
    fallback_file.write_text("{}", encoding="utf-8")

    def find_export_file() -> str:
        result = subprocess.run(
            [
                "bash",
                "-c",
                'set -euo pipefail; source "$1"; find_export_file "$2" C1',
                "bash",
                str(REPO_ROOT / "scripts/lib.sh"),
                str(export_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    assert find_export_file() == str(fallback_file)

    channel_file = export_dir / "C1.json"
    channel_file.write_text("{}", encoding="utf-8")

    assert find_export_file() == str(channel_file)
