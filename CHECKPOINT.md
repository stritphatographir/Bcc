# CHECKPOINT

Updated: 2026-11-27 00:23 Almaty. Owner of this file: the conductor.

## State

- Repo bootstrapped: AGENTS.md (spec + checklist + swarm rules), eval/golden_defects.md, examples/requirements.md, .gitignore.
- Next queue item: refresh sample reports and complete benchmark adjudication. Pending one- and three-vote scoring and report refresh for 17.1, 17.5, 17.6 and 17.7. Item 9 quality gate remains open at 17/30 recall (56.7%), 53/62 reviewed precision (85.5%), 62/84 reviewed. Rules-only recall 5/30. Continue tuning after each change that affects findings.
- Gemini API blocked from this machine (Tor/VPN egress, HTTP 403). Dev LLM: local Qwen at http://monster-server:8080/v1.
- Waiting on the user: final-run LLM (Gemini via non-VPN network, or another key), making the repo public at submission, demo recording.

## Queue (in order)

1. Scaffold: requirements.txt, .env.example, reqcheck/ package, config, LLM client (OpenAI-compatible, cache, retry, JSON validation), CLI.
2. Loader (MD, TXT, PDF, DOCX, HTML) with locators. Make examples/requirements.pdf from the MD.
3. Segmenter (deterministic pre-pass + LLM) and segmentation table.
4. Rule linter.
5. Requirement critics + set critics.
6. Evidence verifier.
7. Clarifier (+ --interactive).
8. Reporter (MD mandatory, HTML, JSON) with all §6 sections.
9. eval/score.py recall vs golden; iterate prompts until recall >= 75% (no doc-specific hardcoding).
10. pytest offline suite.
11. README (RU + short EN), Mermaid architecture diagram.
12. Second sample spec in examples/ for a generality check.
13. Web UI for the demo.
14. Generate reports/report.md (+ html, json) for the sample and commit it.
15. Demo script and slide outline in docs/demo.md.
16. Set up .venv (pytest currently fails: bs4 missing outside a venv); finish uncommitted eval/score.py.
17. Outstanding features from AGENTS.md, in this order: 1 simulator, 5 voting, 6 fintech pack, 7 API critic, 2 test cases, 3 corrected spec, 4 traceability, 8 scores, 9 web UI, 10 trace, 11 benchmark, 12 integrations, 13 diff.
   Re-run items 9 and 14 after each feature that changes findings.

## Conductor task id

mcp:launch:23ccc2a2f4eebf41ce8194d125404263022dbbd57a1cac66f99a2ca04ac12b30

## Quota / reset log

(none yet)

## Done
- 1. CLI scaffold and validated OpenAI-compatible client with retry and cache.
- 2. MD, TXT, PDF, DOCX and HTML loading with source locators and a PDF example.
- 3. Deterministic and model-assisted segmentation with stable IDs and source quotes.
- 4. Russian ambiguity, template, checklist, approval, unit and HTTP rules.
- 5. Concurrent requirement checks and five focused set checks with typed findings.
- 6. Each citation must match its stated locator; normalize whitespace and count dropped findings.
- 7. Prioritized linked questions and pipeline support for terminal answers and targeted rechecks.
- 8. CLI writes Markdown, HTML and JSON with the full report sections and provenance.
- 16. Repaired .venv with Windows Python 3.13 wheels. Dependency install and offline tests pass. Finished the inherited scorer implementation in item 9.
- 10. Offline tests now exercise the CLI end to end, including all three outputs and linter-only fallback.
- 11. Russian quick start and short English guide, provider/key setup, CLI, and Mermaid architecture.
- 12. Added a merchant-settlement sample with cutoff, FX, and duplicate payment cases. Live Qwen confirmed cutoff, duplicate payment and FX date conflicts (209 seconds, 11 API calls).
- 13. Local FastAPI demo uploads a document, streams agent stages, and displays or downloads the full report. Offline API tests pass.
- 14. Reviewed the report with Argon, fixed evidence in summaries and questions, and generated MD, HTML and JSON using a warmed Qwen cache. Cold compact-Qwen sample: 540 seconds, 16 API calls. Latest report: 66 requirements, 84 findings, 4 dropped, 15 cache hits, no failed checks.
- 15. Added a three-minute demo script, five-minute defense outline and jury Q&A.
- 17.1. Typed scenario simulator, independent review and regression tests. Model extraction quality varied on both specs; aligned rule/acceptance pass and score refresh pending.
- 17.5. Majority voting with distinct prompts, confidence and post-vote quote verification. Three-vote run in progress.
- 17.6 and 17.7. Fintech and API checks with verified quotes and scoped regression tests. Live score refresh in progress.
- 17.2, 17.3 and 17.4. Gherkin from resolved scenarios, coverage gaps, proposed requirement diffs with follow-up fixes, and a source-linked traceability table. Test and diff sections are visible through the UI report.
- 17.8. Per-requirement score, observed ISO criteria and HTML readiness charts.
- 17.9. Source quote highlights, answers and rechecks, separate QA tabs, responsive light/dark workspace.
- 17.10. JSONL agent trace, request digests, response counts, timing, provider tokens and cache hits. Trace is also available in the web UI. Browser verification passed source highlights, Q&A and the three QA views (offline path).
- 17.12. Jira CSV/JSON and DOCX exports tested through the CLI. Added a PR workflow for spec changes. GitHub runner not exercised.
- 17.13. Version diff matches moved evidence and retains duplicate occurrences; supports source documents or generated JSON reports.
