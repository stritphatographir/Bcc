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
