import json

import httpx
from fastapi.testclient import TestClient

from reqcheck import pipeline
from reqcheck.config import Settings
from reqcheck.webapp import app


def test_upload_streams_stages_and_report(tmp_path, monkeypatch):
    settings = Settings("http://test/v1", "dummy", "mock", tmp_path)
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda _: settings))
    client_class = pipeline.Client

    def offline(request):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(pipeline, "Client", lambda cfg: client_class(
        cfg, transport=httpx.MockTransport(offline),
    ))
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        response = client.post("/api/analyze", files={
            "document": ("требования.md", "Ф-1. Система должна ответить быстро.".encode()),
        })
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[0] == {"type": "stage", "text": "Чтение документа"}
    final = events[-1]
    assert final["type"] == "result"
    assert final["analysis"]["passport"]["mode"] == "Только правила"
    assert final["analysis"]["findings"][0]["evidence"][0]["locator"] == "строка 1"
    assert final["source"][0]["locator"] == "строка 1"
    assert "Паспорт прогона" in final["markdown"]
    assert 'lang="ru"' in final["html"]


def test_rejects_unsupported_file():
    with TestClient(app) as client:
        response = client.post("/api/analyze", files={"document": ("test.exe", b"abc")})
    assert response.status_code == 415


def test_rejects_malformed_answers():
    with TestClient(app) as client:
        response = client.post("/api/analyze", files={"document": ("test.md", b"data")},
                               data={"answers": "invalid"})
    assert response.status_code == 422
