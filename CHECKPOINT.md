# CHECKPOINT

Updated 2026-11-27 before submission. Owner: conductor.

## Handoff

- Latest demo preflight: the tracked video and report are present; the scorer confirms 25/30 recall and 78/101 precision for the adjudicated report. The current shell has no `python` on PATH; bundled Python runs the scorer but does not include pytest. Earlier clean-venv test results are recorded below.
- Main repository: stritphatographir/Bcc. GitHub has one branch, no PRs, issues or commit comments at the preflight check.
- Deliverables: `examples/requirements.md`, `reports/report.md` (also HTML, JSON and trace), `docs/demo.mp4`. The original file matches the organizer's SHA-256: e7dae55e5453a250d93e335f5ff9c7f775f4457ccddd333f4a67e47b20d74381.
- The Russian video runs 2:46.52 with narration and selectable subtitles. It demonstrates D-101 ? Q-06, the answer, recheck, trace, tests, verdict and benchmark. See `docs/demo.md` for cue points and defense notes.
- Amir controls jury access and submits the repository link, input, generated report and demo by 2026-11-27 23:59 Almaty. Repository private at latest check.

## Verified

- Gemini baseline at `b0e381d`, 2026-11-27: default `gemini-3.8-flash` repeatedly returned HTTP 429. With `gemini-3.5-flash-lite`, Markdown first took 77.34 s (one stage missed the quota window); the full retry took 4.05 s (19 cache hits, one live answer, zero failed stages). PDF was full in 55.29 s (73 requirements, 65 findings); the independent merchant sample was full in 67.45 s (18 requirements, 32 findings). The complete Markdown report has 73 requirements, 62 findings and 50 questions. All 62 findings were adjudicated: recall 18/30 (60.0%), precision 51/62 (82.3%). G20, G27 and G30 are hits. Misses: G01, G02, G05, G06, G13, G14, G15, G16, G19, G21, G23, G25.
- Gemini iteration 1, kept: structural check for a configurable numeric range whose documented default only covers a toggle. G15 added; recall 19/30 (63.3%), precision 52/63 (82.5%). All 32 independent-sample findings identical. Checker caught two boundary cases for explicitly stated defaults; the test covers both. Offline suite: 59 passed.
- Follow-up Gemini setup: `main` synchronized with `origin`; a fresh Windows `.venv` installed all dependencies, `pip check` passed, and `pytest -q` passed all 58 tests, including `tests/test_web.py` (one Starlette deprecation warning). The live baseline awaits a replacement key in the ignored `.env`; the tracked template has an empty key field. No Gemini request was made during setup.
- Project queue items 1?21 complete. CLI, web UI, simulator, evidence check, interactive Clarifier, generated QA artifacts, exports, version diff and scorer are in main. Git history preserves item-level checkpoints.
- Scored Qwen report: 66 requirements, 102 findings, 67 questions, two simulator counterexamples, eight QA cases, four findings dropped. Twenty validated cache hits. Every final citation matched at its locator.
- Evaluation bound to the report hash: 25/30 recall (83.3%); 78 true, 23 false, one undecided, 77.2% precision over 101 decisions. Misses: G14, G15, G20, G21, G23.
- Fresh full MD run in an empty cache: 195 seconds, 20 live Qwen calls, 0 cache hits, no failed stages. Same 66 requirements; 105 findings, all citations verified. Raw result and trace: `eval/runs/qwen-cold.json`. The scored-report annotations apply only to their original report.
- PDF: 252 seconds, 19 live Qwen calls, 1 cache hit, 66 requirements, 100 findings, all citations verified. Independent merchant sample: 17 requirements, 43 findings and 18 questions; every citation verified.
- Real Edge recording: selecting D-101 highlights two source quotes and opens Q-06. The new answer triggered six live responses with four follow-up findings and no failed stage.
- Clean checkout and fresh venv: dependencies installed, pip check clean, 58 offline tests passed. Unreachable endpoint produced a marked rules-only report. Git history scan found no tested credential patterns.
- Gemini live calls remain blocked on this network. Hosted PR workflow and visual DOCX rendering were not tested in this pass. Local Qwen ran successfully; no paid API key was needed.

## Previous night run

- Conductor thread: mcp:launch:23ccc2a2f4eebf41ce8194d125404263022dbbd57a1cac66f99a2ca04ac12b30. Watchdog disabled after the night run. No quota reset pending.
