# AGENTS.md: BCC-HUB x MNU FinTech Hackathon, requirements validator agent

Read this file and `CHECKPOINT.md` before any work. Update `CHECKPOINT.md` after each finished item.

## Hard facts

- Task: https://github.com/BCC-HUB/ai-requirements-validator-task (README in Russian). Sample input: `examples/requirements.md`.
- Our repo: `stritphatographir/Bcc`, branch `main`. Commit small and often. Push after each green item.
- Submission deadline: 2026-11-27 23:59 Almaty (UTC+5). Deliverables: repo + demo of the agent + generated report.
- Night run ends 2026-11-27 08:00 Almaty = 2026-11-27 03:00 UTC.
- Jury: 4 criteria, 25% each:
  1. **Уточнение**: the agent asks the right clarifying questions about the spec.
  2. **Архитектура**: how the agent architecture is built (multi-agent design is judged).
  3. **Ценность**: product quality overall.
  4. **Презентация и защита**: clear demo and defense.
- Mandatory (task README): read the document (PDF required, plus MD/DOCX/TXT), call an LLM, write a report file in Russian.
  One command: `python -m reqcheck <input> -o <report>`. README explains how to get a key, where to put it, the run command, and where the report goes.
  `.env.example` without keys. No secrets in git, ever.
- Report sections (task README §6, all mandatory):
  passport (document name, date, model, agent version = git commit/tag);
  segmentation table "ID в отчёте | ID в документе | краткая формулировка" (assign own IDs plus quote when the document has none);
  check of each requirement; check of the whole set; summary (count of requirements, count of violations, list of critical defects: untestable, contradictory, incomplete);
  verdict (can development and testing start; what to fix first).
  **Every finding cites an exact place and an exact quote from the document. No generic phrases.**
- Criteria: ISO/IEC/IEEE 29148:2018 §5.2.5 (individual: necessary, appropriate, unambiguous, complete, singular, feasible, verifiable, correct, conforming) and §5.2.6 (set: complete, consistent, feasible, comprehensible, able to be validated), plus IEEE 830-1998 §4.3 (correct, unambiguous, complete, consistent, ranked, verifiable, modifiable, traceable). Also flag design leakage (solution in a requirement).

## Winning playbook

Read `.claude/skills/hackathon-playbook/SKILL.md` before work on the report format, Clarifier, README, UI, demo or slides. Background: `research/`.

## Network facts on this machine

- Machine egress IP is in a Tor/VPN range. Google Gemini API returns HTTP 403 from here. Do not burn time on it.
- Dev LLM that works now: local Qwen, OpenAI-compatible, `http://monster-server:8080/v1`, model `swift-1.5-iq3_s`, 262k context, no key needed (send any string).
  It is weak: keep prompts structured, demand JSON, validate, retry on bad JSON.
- The agent must support any OpenAI-compatible endpoint (Gemini has one: `https://generativelanguage.googleapis.com/v1beta/openai/`), so one client covers Gemini, OpenAI, OpenRouter, Ollama, vLLM, local Qwen. Native Anthropic optional.
- Gemini model default must be configurable. `gemini-1.5-flash` in the organizers' example is retired. Do not hardcode a model you cannot verify.

## Architecture (target, judged)

Python 3.11+, package `reqcheck/`. Pipeline of small agents, each with one job, typed I/O (pydantic), all LLM calls through one client with retry, JSON-schema validation, disk cache keyed by prompt hash, temperature 0.

1. **Loader**: PDF (pdfplumber or pypdf), DOCX (python-docx, tables included), MD, TXT, HTML. Keeps line numbers / sections / table rows as locators.
2. **Segmenter agent**: splits into atomic requirements. Keeps document IDs (Ф-1, NFR, table rows, API params, statuses, acceptance criteria rows). Assigns own IDs `R-01..` with section path, locator, verbatim quote. Deterministic pre-pass for numbered items and tables, LLM for the rest.
3. **Rule linter (no LLM)**: Russian weak-word lexicon (быстро, удобно, и т.д., при необходимости, своевременно, достаточно, и/или, около, максимально, ...), empty sections, placeholders (—, TBD, «заполняются»), unfilled checklists, missing version/date/approvers, unit mismatches (тенге vs тиын), HTTP semantics (GET for save), declared-but-undocumented statuses.
4. **Requirement critic agents**: per requirement, check each 29148 §5.2.5 criterion. Output: violated criterion, severity (critical/major/minor), exact quote, why, concrete fix (rewritten requirement text), clarifying question.
5. **Set critic agents**: cross-requirement consistency (pairwise contradictions, e.g. functional rules vs acceptance criteria vs API spec), completeness gaps (missing scenarios, NFR categories, error handling, security/PII, rollback, versioning, traceability), terminology consistency.
6. **Evidence verifier**: drops or repairs any finding whose quote is not found verbatim (normalized whitespace) in the source. This is the anti-hallucination guard. Report the count of dropped findings in the passport.
7. **Clarifier agent** (criterion 1, 25%): turns defects into prioritized questions to the analyst/business owner, grouped by stakeholder, each tied to findings. Interactive mode `--interactive`: asks questions in the terminal, takes answers, re-runs affected checks, and records the Q&A in the report. Non-interactive mode writes the questions into the report.
8. **Reporter**: Markdown report in Russian (mandatory), plus HTML and JSON next to it. Passport includes model, provider, commit, input SHA-256, timestamps, count of LLM calls, cache hits.

Orchestrator runs agents with bounded concurrency. Add a small web UI (FastAPI or Streamlit) for the demo: upload file, watch agent stages, read report, answer clarifying questions. CLI stays the primary path.

## Done-well checklist (Checker scores against this)

1. `pip install -r requirements.txt` then `python -m reqcheck examples/requirements.md -o reports/report.md` works on a clean venv. PDF input works too (make `examples/requirements.pdf`).
2. Report has all §6 sections in Russian. Passport fields are real values, not placeholders.
3. Every finding has a locator and a verbatim quote that exists in the source (verifier enforces it).
4. Recall on `eval/golden_defects.md` at least 75% with the best available model; `python -m eval.score` prints recall and lists misses.
5. Clarifying questions: specific, tied to findings, prioritized, no generic questions.
6. No document-specific facts hardcoded in prompts or code. The agent must work on a different spec. Test on a second, different spec in `examples/`.
7. Secrets: `.env` ignored, `.env.example` present, no keys in git history.
8. README (Russian, plus short English) covers key setup, model choice, one-command run, report location, architecture diagram (Mermaid), agent list.
9. Tests: `pytest` green, offline (LLM mocked), covers loader, segmenter pre-pass, linter, verifier, report rendering.
10. Run time on the sample under 5 min with Gemini Flash class model; graceful degradation (linter-only report) if the LLM is unreachable, marked as such in the passport.

## Outstanding features (goal: 1st place, not "complete")

Build these after the core passes the checklist. Each must be generic (works on any fintech spec), visible in the demo, and covered by a test.

1. **Spec simulator ("агент тестирует ТЗ")**: an agent extracts the business rules into a decision table (conditions, actions, units, time rules), generates edge-case scenarios (boundaries, month/day rollover, time zones, refunds, retries, duplicates, state changes mid-period), and evaluates every acceptance criterion and scenario against the rules. Mismatches become critical findings with the scenario as proof. This is the headline feature.
2. **Generated test cases**: for each requirement, Gherkin scenarios (positive, negative, boundary) and a list of requirements that cannot get a test case (= unverifiable). QA value.
3. **Corrected spec**: a rewritten version of every defective requirement plus a diff view; after `--interactive` answers, the rewrite uses the answers.
4. **Traceability matrix**: goal → functional req → acceptance criterion → API/data → test case, with gaps highlighted.
5. **Self-consistency voting**: run critics N times (default 3 on the free local model, 1 on paid models) and keep findings by vote; show a confidence per finding. Verifier runs after the vote.
6. **Fintech domain pack**: a pluggable checklist critic for banking concerns (money units and rounding, currency, time zones and cut-off, idempotency and retries, refunds and reversals, PII/PCI and card data, audit log, rollback, limits, regulatory notes). Generic, not document-specific.
7. **API contract critic**: HTTP method semantics, status code coverage vs. described responses, request/response type consistency, auth, error model.
8. **Quality scores**: per requirement and per ISO 29148 criterion, a readiness gauge "можно начинать разработку / тестирование", and charts in the HTML report.
9. **Web UI for the demo**: upload, live agent timeline (SSE), the source document with findings highlighted inline (click a finding: scroll to the quote), Q&A panel that triggers a recheck, tabs for test cases, traceability, corrected spec. Polished, Russian, dark/light.
10. **Agent trace**: JSONL trace of each agent step (inputs, outputs, timings, tokens, cache hits) and a trace view in the UI. Architecture judges see the agents work.
11. **Benchmark**: `python -m eval.score` reports recall and precision on the golden set plus an ablation table (linter only, + critics, + simulator, + voting, + verifier). Put the measured table in the README.
12. **Integrations**: Jira-ready CSV/JSON export of findings, a GitHub Action that runs reqcheck on spec changes in a PR, DOCX export of the report.
13. **Version diff**: `reqcheck diff old.md new.md` shows which defects were fixed and which are new.

## Swarm rules

- Pools for this project: the GTA6 project is using both Gemini accounts (`antigravity`, `antigravity_2`) in parallel. Do not use them here, except the Checker exception below.
- **Use local Qwen (`opencode` / `local-qwen/swift-1.5-iq3_s`) as much as possible: it is free and unlimited.** It is weak at reasoning, so give it small, fully specified tasks and verify its output (tests, diff review) before committing.
  Good Qwen jobs: write tests from a spec, write docs drafts, translate RU/EN, generate the second sample spec, run eval and summarize results, mechanical edits with exact instructions, HTML/CSS polish with a clear spec, log reading.
- Conductor: Codex `gpt-6.2-sol` medium. Fallback on quota or failure: `opencode` local Qwen as conductor for small items only, and write the quota reset time to CHECKPOINT.md.
- Code workers: `codex` `gpt-6.1-sol` low/medium for patches Qwen cannot do. Tricky logic (simulator, voting, verifier): `gpt-6.2-sol` medium.
- Workers: one bounded item each, file list given, answer limit 15 lines. Run up to 3 Qwen workers in parallel on different files.
- Checker: Codex work reviewed by `codex` `gpt-6.2-astra` medium. Exception: one cross-family review by `antigravity` `gemini-4-argon` medium before the final report run. At most 2 fix rounds.
- Two workers never write the same file. Only the conductor edits `AGENTS.md` and `CHECKPOINT.md`.
- Claude is rationed: do not delegate to Claude models unless the user asks.
- No paid credits (DeepSeek) without the user's approval. Do not use `opencode/seaglass-alpha-free` for project data.
- A worker with no new evidence after 25 min: cancel it, brief a smaller task.
- Do not make the repo public, submit anything, or post anywhere outside git push to `origin`. The user does that.
