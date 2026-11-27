import os

import pytest

from reqcheck.config import GEMINI_BASE_URL, Settings


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in os.environ:
        if name.startswith(("LLM_", "REQCHECK_")) or name == "GEMINI_API_KEY":
            monkeypatch.delenv(name)
    monkeypatch.setenv("LLM_BASE_URL", "http://primary/v1")
    monkeypatch.setenv("LLM_MODEL", "primary")
    monkeypatch.setenv("LLM_API_KEY", "primary-secret")


def set_backup(monkeypatch, base="http://backup/v1", model="backup"):
    monkeypatch.setenv("REQCHECK_BACKUP_BASE_URL", base)
    monkeypatch.setenv("REQCHECK_BACKUP_MODEL", model)


def test_backup_disabled_by_default():
    settings = Settings.from_env()
    assert settings.backup is None
    assert settings.switch_after == 30
    assert settings.api_key == "primary-secret"


def test_backup_inherits_limits_but_not_primary_credentials_or_extensions(monkeypatch):
    set_backup(monkeypatch)
    monkeypatch.setenv("REQCHECK_TIMEOUT", "75")
    monkeypatch.setenv("REQCHECK_MAX_RETRIES", "2")
    monkeypatch.setenv("REQCHECK_DISABLE_THINKING", "1")
    monkeypatch.setenv("REQCHECK_JSON_SCHEMA", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "google-secret")
    settings = Settings.from_env()
    backup = settings.backup
    assert (backup.base_url, backup.model, backup.api_key) == ("http://backup/v1", "backup", "local")
    assert (backup.cache_dir, backup.timeout, backup.max_retries) == (settings.cache_dir, 75, 2)
    assert not backup.disable_thinking
    assert not backup.use_json_schema
    assert backup.backup is None


def test_explicit_backup_key_and_schema(monkeypatch):
    set_backup(monkeypatch, GEMINI_BASE_URL)
    monkeypatch.setenv("GEMINI_API_KEY", "google-secret")
    monkeypatch.setenv("REQCHECK_BACKUP_API_KEY", "backup-secret")
    monkeypatch.setenv("REQCHECK_BACKUP_JSON_SCHEMA", "1")
    backup = Settings.from_env().backup
    assert backup.api_key == "backup-secret"
    assert backup.use_json_schema


@pytest.mark.parametrize("base", [GEMINI_BASE_URL, "https://generativelanguage.googleapis.com:443/v1beta/openai/"])
def test_google_key_only_for_google_https_origin(monkeypatch, base):
    set_backup(monkeypatch, base)
    monkeypatch.setenv("GEMINI_API_KEY", "google-secret")
    assert Settings.from_env().backup.api_key == "google-secret"


@pytest.mark.parametrize("base", [
    "http://generativelanguage.googleapis.com/v1beta/openai/",
    "https://generativelanguage.googleapis.com.evil.test/v1beta/openai/",
    "https://generativelanguage.googleapis.com@evil.test/v1beta/openai/",
    "https://generativelanguage.googleapis.com:8443/v1beta/openai/",
    "https://evil.test/v1beta/openai/",
])
def test_google_key_not_sent_to_other_origins(monkeypatch, base):
    set_backup(monkeypatch, base)
    monkeypatch.setenv("GEMINI_API_KEY", "google-secret")
    assert Settings.from_env().backup.api_key == "local"


@pytest.mark.parametrize("name,value", [
    ("REQCHECK_BACKUP_BASE_URL", "http://backup/v1"),
    ("REQCHECK_BACKUP_MODEL", "backup"),
    ("REQCHECK_BACKUP_API_KEY", "secret"),
    ("REQCHECK_BACKUP_JSON_SCHEMA", "1"),
    ("REQCHECK_BACKUP_MODEL", ""),
])
def test_incomplete_backup_is_rejected(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="REQCHECK_BACKUP_BASE_URL.*REQCHECK_BACKUP_MODEL"):
        Settings.from_env()


@pytest.mark.parametrize("base", ["http://primary/v1", "http://PRIMARY:80/v1/"])
def test_identical_endpoint_and_model_are_rejected(monkeypatch, base):
    set_backup(monkeypatch, base, "primary")
    with pytest.raises(ValueError, match="backup|резерв",):
        Settings.from_env()


def test_same_endpoint_different_model_is_allowed(monkeypatch):
    set_backup(monkeypatch, "http://primary/v1", "another")
    assert Settings.from_env().backup.model == "another"


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "invalid"])
def test_switch_after_requires_positive_finite_seconds(monkeypatch, value):
    monkeypatch.setenv("REQCHECK_SWITCH_AFTER", value)
    with pytest.raises(ValueError, match="REQCHECK_SWITCH_AFTER"):
        Settings.from_env()


def test_switch_after_can_be_configured(monkeypatch):
    monkeypatch.setenv("REQCHECK_SWITCH_AFTER", "1.25")
    assert Settings.from_env().switch_after == 1.25
