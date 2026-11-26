const form = document.querySelector("#upload");
const start = document.querySelector("#start");
const stages = document.querySelector("#stages");
const status = document.querySelector("#status");
const report = document.querySelector("#report");
const downloads = document.querySelector("#downloads");
const placeholder = document.querySelector("#placeholder");
const views = document.querySelector("#views");
const questions = document.querySelector("#questions");
const recheck = document.querySelector("#recheck");
const rows = new Map();
let result;
let sourceFile;

function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function showPanel(id) {
  document.querySelectorAll(".view").forEach(panel => { panel.hidden = panel.id !== id; });
  views.querySelectorAll("button").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.view === id));
  });
}

views.addEventListener("click", event => {
  if (event.target.dataset.view) showPanel(event.target.dataset.view);
});

function fillSource(event) {
  const source = document.querySelector("#source-lines");
  const findings = document.querySelector("#findings");
  source.replaceChildren();
  findings.replaceChildren();
  rows.clear();
  for (const item of event.source) {
    const row = element("p");
    const content = element("code", item.text);
    row.append(element("span", item.locator), content);
    rows.set(item.locator, { row, content, text: item.text });
    source.append(row);
  }
  event.analysis.findings.forEach((finding, index) => {
    const id = "D-" + String(index + 1).padStart(3, "0");
    const button = element("button", id + " · " + finding.criterion);
    button.type = "button";
    button.title = finding.explanation;
    button.addEventListener("click", () => {
      for (const row of rows.values()) row.content.textContent = row.text;
      for (const evidence of finding.evidence) {
        const item = rows.get(evidence.locator);
        const location = item?.text.indexOf(evidence.quote) ?? -1;
        if (location < 0) continue;
        item.content.replaceChildren(item.text.slice(0, location), element("mark", evidence.quote),
          item.text.slice(location + evidence.quote.length));
      }
      rows.get(finding.evidence[0]?.locator)?.row.scrollIntoView({ block: "center" });
    });
    findings.append(button);
  });
  if (!event.analysis.findings.length) findings.append(element("p", "Подтверждённых дефектов нет."));
}

function fillArtifacts(event) {
  const questionList = document.querySelector("#question-list");
  questionList.replaceChildren();
  recheck.hidden = !event.analysis.questions.length;
  for (const question of event.analysis.questions) {
    const label = element("label", question.id + " · " + question.stakeholder + " · " + question.text);
    const field = element("textarea");
    field.maxLength = 2000;
    field.dataset.id = question.id;
    field.dataset.question = question.text;
    field.value = event.analysis.answers.find(answer => answer.question.id === question.id)?.text ?? "";
    label.append(element("small", question.finding_ids.join(", ")), field);
    questionList.append(label);
  }
  if (recheck.hidden) questionList.append(element("p", "Вопросов по подтверждённым дефектам нет."));

  const tests = document.querySelector("#test-cases");
  tests.replaceChildren();
  for (const test of event.analysis.qa.tests) {
    tests.append(element("h3", test.id + " · " + test.requirements.join(", ")), element("pre", test.gherkin));
  }
  if (event.analysis.qa.uncovered.length) {
    tests.append(element("p", "Без проверяемого результата: " + event.analysis.qa.uncovered.join(", ")));
  }
  const trace = document.querySelector("#trace");
  const table = element("table");
  const header = table.createTHead().insertRow();
  for (const title of ["Цель", "Требование", "Приёмка", "API и данные", "Тесты"]) header.append(element("th", title));
  const body = table.createTBody();
  for (const link of event.analysis.qa.trace) {
    const row = body.insertRow();
    for (const value of [link.goal, link.requirement, link.acceptance.join(", "), link.contracts.join(", "), link.tests.join(", ")]) {
      row.append(element("td", value || "—"));
    }
  }
  trace.replaceChildren(table);
  const rewrites = document.querySelector("#rewrites");
  rewrites.replaceChildren();
  for (const rewrite of event.analysis.qa.rewrites) {
    rewrites.append(element("h3", rewrite.requirement + " · " + rewrite.findings.join(", ")),
      element("pre", rewrite.diff));
  }
  if (!event.analysis.qa.rewrites.length) rewrites.append(element("p", "Предлагаемых правок нет."));

  const agentTrace = document.querySelector("#agent-trace");
  agentTrace.replaceChildren();
  for (const entry of event.analysis.trace) {
    if (entry.status === "start") continue;
    const details = element("details");
    const duration = entry.duration_ms === null ? "" : " · " + entry.duration_ms + " мс";
    details.append(element("summary", entry.agent + " · " + entry.status + duration),
      element("pre", JSON.stringify({ время: entry.time, вход: entry.inputs, выход: entry.outputs }, null, 2)));
    agentTrace.append(details);
  }
}

function showEvent(event) {
  if (event.type === "stage") {
    const item = document.createElement("li");
    item.textContent = event.text;
    stages.append(item);
    status.textContent = event.text;
  } else if (event.type === "error") {
    throw new Error(event.text);
  } else if (event.type === "result") {
    result = event;
    report.srcdoc = event.html;
    fillSource(event);
    fillArtifacts(event);
    views.hidden = false;
    showPanel("report");
    downloads.hidden = false;
    placeholder.hidden = true;
    status.textContent = event.analysis.passport.mode;
  }
}

async function analyze(data) {
  start.disabled = true;
  recheck.disabled = true;
  stages.replaceChildren();
  status.textContent = "Загрузка документа…";

  try {
    const response = await fetch("/api/analyze", { method: "POST", body: data });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(typeof error.detail === "string" ? error.detail : "Проверьте выбранный файл.");
    }
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    let received = false;
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += value;
        const messages = buffer.split("\n\n");
        buffer = messages.pop();
        for (const message of messages) {
          if (!message.startsWith("data: ")) continue;
          const event = JSON.parse(message.slice(6));
          showEvent(event);
          if (event.type === "result") received = true;
        }
      }
      if (!received) throw new Error("Поток отчёта прервался. Повторите проверку.");
    } finally {
      await reader.cancel();
    }
  } catch (error) {
    status.textContent = error.message;
  } finally {
    start.disabled = false;
    recheck.disabled = false;
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  const data = new FormData(form);
  const file = data.get("document");
  views.hidden = true;
  showPanel("");
  downloads.hidden = true;
  placeholder.hidden = false;
  result = undefined;
  sourceFile = file;
  void analyze(data);
});

questions.addEventListener("submit", event => {
  event.preventDefault();
  const answers = Array.from(questions.querySelectorAll("textarea"), field => ({
    id: field.dataset.id, question: field.dataset.question, text: field.value.trim(),
  })).filter(answer => answer.text);
  if (!answers.length || !sourceFile) {
    status.textContent = "Введите хотя бы один ответ.";
    return;
  }
  const data = new FormData();
  data.set("document", sourceFile);
  data.set("answers", JSON.stringify(answers));
  void analyze(data);
});

downloads.addEventListener("click", event => {
  const format = event.target.dataset.format;
  if (!format || !result) return;
  const contents = { md: result.markdown, html: result.html, json: JSON.stringify(result.analysis, null, 2),
    jsonl: result.analysis.trace.map(entry => JSON.stringify(entry)).join("\n") + "\n" };
  const url = URL.createObjectURL(new Blob([contents[format]]));
  const link = document.createElement("a");
  link.href = url;
  link.download = format === "jsonl" ? "report.trace.jsonl" : "report." + format;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
