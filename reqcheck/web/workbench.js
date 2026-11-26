const form = document.querySelector("#upload");
const start = document.querySelector("#start");
const stages = document.querySelector("#stages");
const status = document.querySelector("#status");
const report = document.querySelector("#report");
const downloads = document.querySelector("#downloads");
const placeholder = document.querySelector("#placeholder");
let result;

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
    report.hidden = false;
    downloads.hidden = false;
    placeholder.hidden = true;
    status.textContent = event.analysis.passport.mode;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  start.disabled = true;
  report.hidden = true;
  downloads.hidden = true;
  placeholder.hidden = false;
  result = undefined;
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
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += value;
        const messages = buffer.split("\n\n");
        buffer = messages.pop();
        for (const message of messages) {
          if (message.startsWith("data: ")) showEvent(JSON.parse(message.slice(6)));
        }
      }
      if (!result) throw new Error("Поток отчёта прервался. Повторите проверку.");
    } finally {
      await reader.cancel();
    }
  } catch (error) {
    status.textContent = error.message;
  } finally {
    start.disabled = false;
  }
});

downloads.addEventListener("click", event => {
  const format = event.target.dataset.format;
  if (!format || !result) return;
  const contents = { md: result.markdown, html: result.html, json: JSON.stringify(result.analysis, null, 2) };
  const url = URL.createObjectURL(new Blob([contents[format]]));
  const link = document.createElement("a");
  link.href = url;
  link.download = "report." + format;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
