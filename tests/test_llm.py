import json

import httpx
from pydantic import BaseModel

from reqcheck.llm import Client
from reqcheck.config import Settings


class Result(BaseModel):
    answer: int


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
