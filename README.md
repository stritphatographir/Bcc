# reqcheck — агент проверки требований

Агент читает документ с требованиями (PDF, DOCX, MD, TXT, HTML) и пишет отчёт на русском.
Отчёт содержит: паспорт прогона, таблицу сегментации, проверку каждого требования и набора,
уточняющие вопросы, сводку и вердикт. Каждый вывод подкреплён точной цитатой и местом в документе.

## Установка

Требуется Python 3.11 или новее.

```bash
git clone https://github.com/stritphatographir/Bcc.git
cd Bcc
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ключ модели и выбор модели

Скопируйте `.env.example` в `.env` и заполните. Файл `.env` не попадает в git.

**Gemini.** Получите ключ на <https://aistudio.google.com/apikey>, затем в `.env`:

```dotenv
GEMINI_API_KEY=<ваш ключ>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=<идентификатор актуальной модели Gemini из списка>
```

Выберите модель из [списка Gemini](https://ai.google.dev/gemini-api/docs/models) и укажите её ID.
Оставьте `LLM_API_KEY` пустым, чтобы клиент использовал `GEMINI_API_KEY`.

**Локальный endpoint (OpenAI-совместимый: Ollama, vLLM, LM Studio).** Ключ не нужен:

```dotenv
LLM_BASE_URL=http://monster-server:8080/v1
LLM_MODEL=swift-1.5-iq3_s
LLM_API_KEY=
```

Для другого OpenAI-совместимого провайдера задайте его `LLM_BASE_URL`, `LLM_MODEL` и
`LLM_API_KEY`. `REQCHECK_TIMEOUT` задаёт тайм-аут запроса в секундах.
Сервер Qwen поддерживает `REQCHECK_DISABLE_THINKING=1` для запуска без фазы рассуждения.

## Запуск (одна команда)

```bash
python -m reqcheck examples/requirements.md -o reports/report.md
```

Отчёт пишется в три файла: `reports/report.md`, `reports/report.html`, `reports/report.json`.
В консоль (`stderr`) печатаются этапы работы агентов. Если модель недоступна, агент
выдаёт отчёт только с правилами линтера и помечает это в паспорте как «Только правила».

Интерактивный режим: агент задаёт уточняющие вопросы в терминале, принимает ответы,
перепроверяет затронутые требования и пишет диалог в отчёт:

```bash
python -m reqcheck examples/requirements.md -o reports/report.md --interactive
```

## Что внутри отчёта

- **Паспорт прогона**: документ, SHA-256, модель, провайдер, версия из git, время,
  число обращений к LLM, попадания кэша, число отброшенных выводов, режим проверки.
- **Каждый вывод**: нарушение, серьёзность, точная цитата, локатор (строка/раздел/таблица),
  объяснение и переписанная формулировка требования.
- **Сверка цитат (Evidence Verifier)** проверяет совпадение цитаты с исходным текстом
  по указанному локатору. Число отброшенных выводов указано в паспорте.
- **Уточняющие вопросы**: сгруппированы по адресатам, привязаны к ID выводов.

## Веб-демо

```bash
python -m uvicorn reqcheck.webapp:app --host 127.0.0.1 --port 8000
```

Откройте <http://127.0.0.1:8000>, загрузите файл и дождитесь завершения этапов.
В отчёте доступны точные цитаты и вопросы. Кнопки экспорта сохраняют Markdown, HTML и JSON.
Для проверки после ответов используйте запуск с `--interactive`.

## Архитектура

Каждый агент делает одну работу, передача данных типизирована (pydantic), все обращения
к LLM идут через один клиент (retry, JSON-схема, кэш по хешу промпта, temperature 0).

```mermaid
flowchart LR
    O["Orchestrator · pipeline.analyze"] --> L[Loader]
    L --> S["Segmenter · LLM"]
    S --> RL["Rule Linter"]
    S --> C["Requirement Critic и Set Critic · LLM"]
    RL --> V["Evidence Verifier"]
    C --> V
    V --> Q[Clarifier]
    Q --> R["Reporter · MD, HTML, JSON"]
    O -.-> U["Этапы в stderr"]
```

## Тесты без сети

```bash
pytest
```

Тесты используют имитацию ответов модели и выполняются без сети.

## Измерение качества

Как считать полноту и точность по эталону — в `eval/README.md`
(команда `python -m eval.score`).

---

## English (short)

`reqcheck` reads a requirements document (PDF/DOCX/MD/TXT/HTML) and writes a Russian
report: run passport, segmentation table, per-requirement and set-level checks,
prioritized clarifying questions, summary and verdict. Every finding carries a verbatim
quote and a locator; an Evidence Verifier drops findings whose quote is not in the source.
Set `GEMINI_API_KEY` + `LLM_MODEL` (no retired default — set a current Gemini model) or
point `LLM_BASE_URL`/`LLM_API_KEY` at any OpenAI-compatible endpoint, including a local
model. Run: `python -m reqcheck examples/requirements.md -o reports/report.md`
(MD + HTML + JSON). `--interactive` asks clarifying questions and re-checks. `pytest`
runs offline with a mocked LLM.
