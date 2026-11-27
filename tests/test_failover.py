import asyncio
import threading
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from time import monotonic

import httpx
import pytest
from pydantic import BaseModel

from reqcheck.config import Settings
from reqcheck.llm import Client, LLMError
from reqcheck.trace import TraceLog


class Answer(BaseModel):
    answer: int


def settings(cache, *, limit=0.25):
    backup = Settings("http://backup/v1", "backup-key", "second", cache)
    return Settings("http://primary/v1", "primary-key", "first", cache,
                    backup=backup, switch_after=limit)


def ok(value):
    return httpx.Response(200, json={"choices": [{"message": {"content": '{"answer": %d}' % value}}]})


@pytest.mark.parametrize("endpoint_timeout", [40, 1])
def test_connection_timeout_is_separate_from_response_timeout(tmp_path, endpoint_timeout):
    config = replace(settings(tmp_path, limit=30), timeout=endpoint_timeout)
    async def reply(request):
        if request.url.host == "primary":
            timeout = request.extensions["timeout"]
            assert timeout["connect"] == min(3, endpoint_timeout)
            assert timeout["read"] == endpoint_timeout
            raise httpx.ConnectTimeout("silent connection attempt")
        return ok(2)
    with Client(config, transport=httpx.MockTransport(reply)) as client:
        assert client.ask("first", {}, Answer).answer == 2
        assert client.switch_reason == "ConnectTimeout"
        assert [run["calls"] for run in client.model_runs] == [1, 1]


def test_concurrent_stalls_switch_once_and_cancel_primary(tmp_path):
    lock = threading.Lock()
    seen, cancelled, announced = [], [], []

    async def reply(request):
        host = request.url.host
        assert request.headers["Authorization"] == f"Bearer {host}-key"
        with lock:
            seen.append(host)
        if host == "primary":
            try:
                await asyncio.sleep(5)
            finally:
                cancelled.append(host)
        return ok(2)

    start = monotonic()
    with Client(settings(tmp_path), transport=httpx.MockTransport(reply)) as client:
        client.trace = TraceLog()
        client.on_switch = announced.append
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda t: client.ask(t, {}, Answer).answer, ["a", "b"]))
        assert answers == [2, 2]
        assert client.ask("c", {}, Answer).answer == 2
        assert client.ask("a", {}, Answer).answer == 2
        assert len(announced) == 1
        assert len([e for e in client.trace.events if e.status == "switch"]) == 1
        assert [(x["calls"], x["responses"], x["cache_hits"]) for x in client.model_runs] == [(2, 0, 0), (3, 3, 1)]
    assert len(cancelled) == 2 and seen.count("primary") == 2
    assert monotonic() - start < 3


def test_no_backup_network_on_success_and_cache_is_provider_specific(tmp_path):
    hosts = []
    async def reply(request):
        hosts.append(request.url.host)
        return ok(1)
    with Client(settings(tmp_path), transport=httpx.MockTransport(reply)) as client:
        assert client.ask("x", {}, Answer).answer == 1
        assert client.ask("x", {}, Answer).answer == 1
        assert client.model_runs == [] and not client.switch_reason
    assert hosts == ["primary"]


def test_retry_after_exceeds_budget_and_dead_backup_stops(tmp_path):
    hosts = []
    async def reply(request):
        hosts.append(request.url.host)
        if request.url.host == "primary":
            return httpx.Response(429, headers={"retry-after": "60"})
        raise httpx.ConnectError("offline")
    with Client(settings(tmp_path), transport=httpx.MockTransport(reply)) as client:
        for task in ("first", "next"):
            with pytest.raises(LLMError):
                client.ask(task, {}, Answer)
        assert client.offline
    assert hosts == ["primary", "backup"]


@pytest.mark.parametrize("failure", ["unavailable", "disconnected", "proxy"])
def test_completed_checks_survive_loss_of_primary(tmp_path, failure):
    hosts = []
    async def reply(request):
        host = request.url.host
        hosts.append(host)
        if len(hosts) == 2:
            if failure == "proxy":
                raise httpx.ProxyError("proxy offline")
            if failure == "disconnected":
                raise httpx.RemoteProtocolError("connection closed")
            return httpx.Response(503)
        return ok(1 if host == "primary" else 2)
    config = replace(settings(tmp_path), max_retries=1)
    with Client(config, transport=httpx.MockTransport(reply)) as client:
        assert client.ask("first", {}, Answer).answer == 1
        assert client.ask("second", {}, Answer).answer == 2
        assert [r["responses"] for r in client.model_runs] == [1, 1]
    assert hosts == ["primary", "primary", "backup"]
