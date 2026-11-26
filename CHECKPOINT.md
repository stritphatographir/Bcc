# CHECKPOINT

Updated: 2026-11-26 23:56 Almaty. Owner of this file: the conductor.

## State

- Repo bootstrapped: AGENTS.md (spec + checklist + swarm rules), eval/golden_defects.md, examples/requirements.md, .gitignore.
- Next queue item: 9. Scorer and tests ready. Rules-only baseline 5/30 recall (16.7%), reviewed precision 21/21. Live Qwen report still running.
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
