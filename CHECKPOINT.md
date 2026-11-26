# CHECKPOINT

Updated: 2026-11-26 23:38 Almaty. Owner of this file: the conductor.

## State

- Repo bootstrapped: AGENTS.md (spec + checklist + swarm rules), eval/golden_defects.md, examples/requirements.md, .gitignore.
- Next queue item: 4.
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

## Quota / reset log

(none yet)

## Done
- 1. CLI scaffold and validated OpenAI-compatible client with retry and cache.
- 2. MD, TXT, PDF, DOCX and HTML loading with source locators and a PDF example.
- 3. Deterministic and model-assisted segmentation with stable IDs and source quotes.
