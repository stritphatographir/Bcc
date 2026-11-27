import json

import httpx
from pydantic import BaseModel

from reqcheck.llm import Client, LLMError
from reqcheck.config import Settings


class Result(BaseModel):
    answer: int


def test_server_schema_mode_has_its_own_validated_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_BASE_URL", "http://test/v1")
    monkeypatch.setenv("LLM_MODEL", "test")
    monkeypatch.delenv("REQCHECK_JSON_SCHEMA", raising=False)
    formats = []
    contents = iter(['{"answer": 1}', '{"wrong": 2}', '{"answer": 2}'])

    def respond(request):
        formats.append(json.loads(request.content).get("response_format"))
        return httpx.Response(200, json={"choices": [{"message": {"content": next(contents)}}]})

    transport = httpx.MockTransport(respond)
    with Client(Settings.from_env(), transport=transport) as ordinary:
        assert ordinary.ask("task", {}, Result).answer == 1
    monkeypatch.setenv("REQCHECK_JSON_SCHEMA", "1")
    with Client(Settings.from_env(), transport=transport) as constrained:
        assert constrained.ask("task", {}, Result).answer == 2
        assert (constrained.calls, constrained.responses, constrained.hits) == (2, 1, 0)
        assert constrained.ask("task", {}, Result).answer == 2
        assert constrained.hits == 1
    expected = {"type": "json_schema", "json_schema": {"name": "Result", "schema": Result.model_json_schema()}}
    assert formats == [None, expected, expected]


def test_retry_and_cache(tmp_path):
    responses = iter(["not JSON", '{"answer": 42}'])

    def respond(request):
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": next(responses)}}]})

    settings = Settings("http://test/v1", "dummy", "test", tmp_path)
    with Client(settings, transport=httpx.MockTransport(respond)) as client:
        assert client.ask("task", {"input": "data"}, Result).answer == 42
        assert client.ask("task", {"input": "data"}, Result).answer == 42
        assert (client.calls, client.hits) == (2, 1)


def test_thinking_override_is_opt_in_and_part_of_cache_key(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://test/v1")
    monkeypatch.setenv("LLM_MODEL", "test")
    monkeypatch.setenv("REQCHECK_DISABLE_THINKING", "1")
    assert Settings.from_env().disable_thinking is True
    settings = Settings("http://test/v1", "dummy", "test", tmp_path, disable_thinking=True)
    payloads = []

    def respond(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"answer": 42}'}}]})

    transport = httpx.MockTransport(respond)
    with Client(settings, transport=transport) as client:
        client.ask("task", {}, Result)
    ordinary = Settings("http://test/v1", "dummy", "test", tmp_path)
    with Client(ordinary, transport=transport) as client:
        client.ask("task", {}, Result)
    assert payloads[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert "chat_template_kwargs" not in payloads[1]


def test_rate_limit_backs_off_using_retry_after(tmp_path):
    replies = iter([
        httpx.Response(429, headers={"retry-after": "7"}),
        httpx.Response(503),
        httpx.Response(200, json={"choices": [{"message": {"content": '{"answer": 1}'}}]}),
    ])
    settings = Settings("http://test/v1", "dummy", "test", tmp_path)
    with Client(settings, transport=httpx.MockTransport(lambda request: next(replies))) as client:
        waits = []
        client.sleep = waits.append
        assert client.ask("task", {}, Result).answer == 1
    assert waits == [7.0, 4.0]
    assert (client.calls, client.responses) == (3, 1)


def test_fatal_error_stops_further_calls(tmp_path):
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(400, json={"error": {"message": "API key not valid. Please pass a valid API key."}})

    settings = Settings("http://test/v1", "dummy", "test", tmp_path)
    with Client(settings, transport=httpx.MockTransport(respond)) as client:
        for task in ("one", "two", "three"):
            try:
                client.ask(task, {}, Result)
            except LLMError as exc:
                assert "HTTP 400" in str(exc)
    assert len(seen) == 1
    assert "неверный ключ" in client.offline


def test_gemini_is_the_default_provider(monkeypatch):
    for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "REQCHECK_CRITIC_VOTES", "REQCHECK_CONCURRENCY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.chdir("/")
    settings = Settings.from_env()
    assert settings.base_url.startswith("https://generativelanguage.googleapis.com/")
    assert settings.model.startswith("gemini-")
    assert settings.api_key == "test-key"
    assert (settings.critic_votes, settings.concurrency) == (1, 2)
