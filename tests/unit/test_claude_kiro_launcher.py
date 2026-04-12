# -*- coding: utf-8 -*-

"""
Unit tests for the claude-kiro launcher script.

Verifies:
- Shell syntax is valid
- The launcher forwards Anthropic gateway environment variables to Claude Code
"""

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER_PATH = REPO_ROOT / "bin" / "claude-kiro"
COMMON_HELPER_PATH = REPO_ROOT / "bin" / "_kiro_gateway_common.sh"
START_SCRIPT_PATH = REPO_ROOT / "bin" / "kiro-gateway-start"
STOP_SCRIPT_PATH = REPO_ROOT / "bin" / "kiro-gateway-stop"
SHELL_SCRIPT_PATHS = (
    LAUNCHER_PATH,
    COMMON_HELPER_PATH,
    START_SCRIPT_PATH,
    STOP_SCRIPT_PATH,
)


def create_script_symlink(tmp_path: Path, source_path: Path) -> Path:
    """
    Create a temporary symlink to a launcher script.

    Args:
        tmp_path: Pytest-provided temporary directory.
        source_path: Absolute path to the source script in the repo.

    Returns:
        Path to the created symlink.
    """
    symlink_dir = tmp_path / "linked-bin"
    symlink_dir.mkdir()
    symlink_path = symlink_dir / source_path.name
    symlink_path.symlink_to(source_path)
    return symlink_path


class TestClaudeKiroLauncher:
    """Tests for the bin/claude-kiro launcher script."""

    def test_scripts_have_valid_shell_syntax(self):
        """
        What it does: Validates each shell script with `sh -n`.
        Purpose: Catch shell syntax regressions before runtime.
        """
        for script_path in SHELL_SCRIPT_PATHS:
            print(f"Action: Running shell syntax check for {script_path.name}...")
            result = subprocess.run(
                ["sh", "-n", str(script_path)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
            )

            print(f"Exit code: {result.returncode}")
            if result.stderr:
                print(f"stderr: {result.stderr}")
            assert result.returncode == 0, script_path.name

    def test_launcher_passes_gateway_environment_to_claude(self, tmp_path):
        """
        What it does: Executes the launcher with mocked curl and claude binaries.
        Purpose: Ensure Claude Code receives the expected Anthropic proxy env vars.
        """
        print("Setup: Creating mocked curl and claude commands...")
        mock_bin_dir = tmp_path / "bin"
        mock_bin_dir.mkdir()

        output_file = tmp_path / "claude-output.txt"
        curl_script = mock_bin_dir / "curl"
        curl_script.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            "  *\"/health\"*) exit 0 ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        curl_script.chmod(0o755)

        claude_script = mock_bin_dir / "claude"
        claude_script.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$ANTHROPIC_BASE_URL\" > \"$CLAUDE_KIRO_TEST_OUTPUT\"\n"
            "printf '%s\\n' \"$ANTHROPIC_AUTH_TOKEN\" >> \"$CLAUDE_KIRO_TEST_OUTPUT\"\n"
            "printf '%s\\n' \"$ANTHROPIC_DEFAULT_SONNET_MODEL\" >> \"$CLAUDE_KIRO_TEST_OUTPUT\"\n"
            "printf '%s\\n' \"$*\" >> \"$CLAUDE_KIRO_TEST_OUTPUT\"\n",
            encoding="utf-8",
        )
        claude_script.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
        env["CLAUDE_KIRO_TEST_OUTPUT"] = str(output_file)
        env["KIRO_GATEWAY_HOST"] = "127.0.0.1"
        env["KIRO_GATEWAY_PORT"] = "8019"
        env["KIRO_GATEWAY_PROXY_API_KEY"] = "launcher-test-key"
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = "claude-sonnet-4.6"
        launcher_symlink = create_script_symlink(tmp_path, LAUNCHER_PATH)

        print("Action: Executing launcher...")
        result = subprocess.run(
            [str(launcher_symlink), "--print", "hello"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )

        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")

        launcher_output = output_file.read_text(encoding="utf-8").splitlines()
        print(f"Captured launcher output: {launcher_output}")

        assert result.returncode == 0
        assert launcher_output[0] == "http://127.0.0.1:8019"
        assert launcher_output[1] == "launcher-test-key"
        assert launcher_output[2] == "claude-sonnet-4.6"
        assert launcher_output[3] == "--print hello"

    def test_launcher_preserves_claude_exit_code(self, tmp_path):
        """
        What it does: Executes the launcher with a failing mocked Claude binary.
        Purpose: Ensure wrapper logic does not mask Claude Code failures.
        """
        print("Setup: Creating mocked curl and failing claude commands...")
        mock_bin_dir = tmp_path / "bin"
        mock_bin_dir.mkdir()

        curl_script = mock_bin_dir / "curl"
        curl_script.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            "  *\"/health\"*) exit 0 ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        curl_script.chmod(0o755)

        claude_script = mock_bin_dir / "claude"
        claude_script.write_text(
            "#!/bin/sh\n"
            "exit 17\n",
            encoding="utf-8",
        )
        claude_script.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
        env["KIRO_GATEWAY_HOST"] = "127.0.0.1"
        env["KIRO_GATEWAY_PORT"] = "8022"
        launcher_symlink = create_script_symlink(tmp_path, LAUNCHER_PATH)

        print("Action: Executing launcher...")
        result = subprocess.run(
            [str(launcher_symlink)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )

        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")

        assert result.returncode == 17


class TestGatewayControlScripts:
    """Tests for kiro-gateway-start and kiro-gateway-stop."""

    def test_start_script_reports_existing_gateway(self, tmp_path):
        """
        What it does: Runs kiro-gateway-start when health checks already pass.
        Purpose: Verify the script reports an existing gateway without spawning a new one.
        """
        print("Setup: Creating mocked curl command and an existing PID file...")
        mock_bin_dir = tmp_path / "bin"
        mock_bin_dir.mkdir()

        curl_script = mock_bin_dir / "curl"
        curl_script.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            "  *\"/health\"*) exit 0 ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        curl_script.chmod(0o755)

        sleeper = subprocess.Popen(["sleep", "60"], cwd=REPO_ROOT)
        pid_file = tmp_path / "kiro-gateway.pid"
        pid_file.write_text(f"{sleeper.pid}\n", encoding="utf-8")

        env = os.environ.copy()
        env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
        env["KIRO_GATEWAY_HOST"] = "127.0.0.1"
        env["KIRO_GATEWAY_PORT"] = "8020"
        env["KIRO_GATEWAY_PID_FILE"] = str(pid_file)
        start_symlink = create_script_symlink(tmp_path, START_SCRIPT_PATH)

        try:
            print("Action: Executing kiro-gateway-start...")
            result = subprocess.run(
                [str(start_symlink)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                env=env,
                check=False,
            )
        finally:
            sleeper.terminate()
            sleeper.wait(timeout=5)

        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")

        assert result.returncode == 0
        assert "already running" in result.stderr
        assert f"PID: {pid_file.read_text(encoding='utf-8').strip()}" in result.stderr
        assert "Health: http://127.0.0.1:8020/health" in result.stderr

    def test_stop_script_terminates_pid_from_file(self, tmp_path):
        """
        What it does: Runs kiro-gateway-stop against a PID file backed by a real process.
        Purpose: Ensure the script stops the process and removes the PID file.
        """
        print("Setup: Starting a real background process for stop testing...")
        sleeper = subprocess.Popen(["sleep", "60"], cwd=REPO_ROOT)
        pid_file = tmp_path / "kiro-gateway.pid"
        pid_file.write_text(f"{sleeper.pid}\n", encoding="utf-8")

        env = os.environ.copy()
        env["KIRO_GATEWAY_PORT"] = "8021"
        env["KIRO_GATEWAY_PID_FILE"] = str(pid_file)
        stop_symlink = create_script_symlink(tmp_path, STOP_SCRIPT_PATH)

        print("Action: Executing kiro-gateway-stop...")
        result = subprocess.run(
            [str(stop_symlink)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )

        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")

        sleeper.wait(timeout=5)

        assert result.returncode == 0
        assert not pid_file.exists()
        assert "Stopping Kiro Gateway PID" in result.stderr
        assert "Kiro Gateway stopped." in result.stderr
