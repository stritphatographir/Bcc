import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest
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


def test_workbench_finding_question_navigation_and_recheck():
    """Run the shipped JS with a small DOM double; no browser dependency required."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is unavailable")
    script = r'''
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.listeners = {}; this.hidden = false; this.value = ""; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this[key] = value; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  querySelectorAll(tag) { return this.children.flatMap(child => typeof child === "string" ? [] : [...(child.tag === tag ? [child] : []), ...child.querySelectorAll(tag)]); }
  scrollIntoView() { this.scrolled = true; }
  focus() { focused = this; }
  createTHead() { return new Element("thead"); }
  createTBody() { return new Element("tbody"); }
  insertRow() { return new Element("tr"); }
}
let focused;
const nodes = new Map();
const document = {
  querySelector(id) { if (!nodes.has(id)) nodes.set(id, new Element(id)); return nodes.get(id); },
  querySelectorAll(selector) { return selector === ".view" ? ["report", "source", "questions"].map(id => { const n = document.querySelector("#" + id); n.id = id; return n; }) : []; },
  createElement(tag) { return new Element(tag); }
};
const context = vm.createContext({ document, console, FormData, setTimeout });
vm.runInContext(fs.readFileSync("reqcheck/web/workbench.js", "utf8"), context);
const finding = { criterion: "Проверяемость", explanation: "Срок не задан", evidence: [{ locator: "строка 1", quote: "быстро" }] };
const question = { id: "Q-01", stakeholder: "Аналитик", text: "Какой срок?", finding_ids: ["D-001", "D-002"] };
const event = { type: "result", html: "report", source: [{locator: "строка 1", text: "Ответить быстро"}], analysis: {
  findings: [finding, finding, finding], questions: [question], answers: [], passport: {mode: "Только правила"},
  qa: {tests: [], uncovered: [], trace: [], rewrites: []}, trace: []
}};
context.payload = event;
vm.runInContext("showEvent(payload)", context);
const findingButtons = document.querySelector("#findings").querySelectorAll("button");
findingButtons[1].listeners.click();
const related = document.querySelector("#finding-questions").querySelectorAll("button");
assert.equal(related.length, 1);
assert.match(related[0].textContent, /D-002.*Q-01/);
related[0].listeners.click();
const field = document.querySelector("#question-list").querySelectorAll("textarea")[0];
assert.equal(focused, field);
assert.equal(field.scrolled, true);
assert.equal(document.querySelector("#questions").hidden, false);
findingButtons[2].listeners.click();
assert.equal(document.querySelector("#finding-questions").querySelectorAll("button").length, 0);
assert.match(document.querySelector("#finding-questions").children[0].textContent, /D-003/);
(async () => {
  context.fetch = async () => ({ok: true, body: {pipeThrough: () => ({getReader: () => {
    let read = false;
    return {read: async () => read ? {done: true} : (read = true, {done: false, value: "data: " + JSON.stringify(context.payload) + "\n\n"}), cancel: async () => {}};
  }})}});
  context.TextDecoderStream = class {};
  event.analysis.answers = [{question, text: "2 секунды"}];
  await vm.runInContext("analyze(new FormData(), true)", context);
  assert.match(document.querySelector("#answer-status").textContent, /Сохранено ответов: 1/);
  assert.equal(document.querySelector("#questions").hidden, false);
  context.payload = {type: "error", text: "Вопросы изменились"};
  await vm.runInContext("analyze(new FormData(), true)", context);
  assert.match(document.querySelector("#answer-status").textContent, /не подтверждены.*Вопросы изменились/);
  assert.doesNotMatch(document.querySelector("#answer-status").textContent, /Сохранено/);
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    completed = subprocess.run([node, "-e", script], cwd=Path(__file__).parents[1],
                               capture_output=True, text=True, encoding="utf-8")
    assert completed.returncode == 0, completed.stdout + completed.stderr
