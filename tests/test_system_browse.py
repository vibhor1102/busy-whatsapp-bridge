import subprocess
import asyncio

from app.main import _browse_system_file_blocking, browse_system_file


class _Result:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_browse_system_file_success(monkeypatch):
    monkeypatch.setattr(
        "app.main._run_windows_powershell",
        lambda script, timeout_seconds=45: _Result(stdout=r"C:\Data\db12025.bds", returncode=0),
    )
    result = _browse_system_file_blocking()
    assert result["success"] is True
    assert result["path"].endswith("db12025.bds")


def test_browse_system_file_cancelled(monkeypatch):
    monkeypatch.setattr(
        "app.main._run_windows_powershell",
        lambda script, timeout_seconds=45: _Result(stdout="", stderr="", returncode=0),
    )
    result = _browse_system_file_blocking()
    assert result["success"] is False
    assert result["reason"] == "cancelled"
    assert result["timeout"] is False


def test_browse_system_file_powershell_error(monkeypatch):
    monkeypatch.setattr(
        "app.main._run_windows_powershell",
        lambda script, timeout_seconds=45: _Result(stdout="", stderr="boom", returncode=1),
    )
    result = _browse_system_file_blocking()
    assert result["success"] is False
    assert result["reason"] == "powershell_error"
    assert result["stderr"] == "boom"


def test_browse_system_file_timeout(monkeypatch):
    def _timeout(script, timeout_seconds=45):
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=timeout_seconds)

    monkeypatch.setattr("app.main._run_windows_powershell", _timeout)
    result = _browse_system_file_blocking()
    assert result["success"] is False
    assert result["reason"] == "timeout"
    assert result["timeout"] is True


def test_browse_endpoint_returns_failure_payload(monkeypatch):
    monkeypatch.setattr(
        "app.main._browse_system_file_blocking",
        lambda: {
            "path": None,
            "success": False,
            "reason": "powershell_error",
            "stderr": "boom",
            "timeout": False,
            "exit_code": 1,
            "message": "Failed to open file browser",
        },
    )
    result = asyncio.run(browse_system_file())
    assert result["success"] is False
    assert result["reason"] == "powershell_error"
    assert result["stderr"] == "boom"
