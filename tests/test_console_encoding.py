import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("encoding", ["cp1252", None])
def test_score_console_is_utf8(encoding):
    env = dict(os.environ, PYTHONUTF8="0")
    env.pop("PYTHONIOENCODING", None)
    if encoding:
        env["PYTHONIOENCODING"] = encoding
    completed = subprocess.run(
        [sys.executable, "-m", "eval.score"],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    assert "Оценено выводов" in completed.stdout.decode("utf-8")
    assert "Traceback" not in completed.stderr.decode("utf-8")


@pytest.mark.parametrize("encoding", ["cp1252", None])
def test_reqcheck_stage_console_is_utf8(tmp_path, encoding):
    env = dict(os.environ, PYTHONUTF8="0", LLM_BASE_URL="http://127.0.0.1:1/v1",
               LLM_MODEL="offline-test", REQCHECK_MAX_RETRIES="0", REQCHECK_TIMEOUT="0.01")
    env.pop("PYTHONIOENCODING", None)
    if encoding:
        env["PYTHONIOENCODING"] = encoding
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "reqcheck", "examples/requirements.md", "-o", str(tmp_path / "report.md")],
        cwd=root, env=env, capture_output=True, timeout=60,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    stages = completed.stderr.decode("utf-8")
    assert "Чтение документа" in stages
    assert "\\u04" not in stages
    assert "Traceback" not in stages
