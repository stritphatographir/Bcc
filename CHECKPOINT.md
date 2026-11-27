# CHECKPOINT

Updated: 2026-11-27, jury preparation. Owner of this file: the conductor.

## State

- Repo bootstrapped: AGENTS.md (spec + checklist + swarm rules), eval/golden_defects.md, examples/requirements.md, .gitignore.
- Queue through item 21 complete. Jury audit reviewed all 102 findings. Recall 25/30 (83.3%); precision 78/101 (77.2%); one undecided pending the authentication contract.
- Gemini API blocked from this machine (Tor/VPN egress, HTTP 403). Dev LLM: local Qwen at http://monster-server:8080/v1.
- Session 2026-11-27 (Claude): jury-readiness pass, items 18–21 below.
- Submission uses the scored local Qwen report and the recorded Russian demo. Amir controls jury access and submission.

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
18. Jury run path: Gemini default provider and model, 429/5xx backoff, fail-fast offline mode, honest passport counts.
19. Explicit §6 verdict (development / testing yes-no-conditional) and de-duplicated first fixes.
20. Clarifier: merge paraphrased questions, route by citations, cap --interactive.
21. Structure checks without LLM: happy-path-only diagrams (G27), rule duplicated across sections (G30).

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
- 17.1. Typed scenario simulator, independent review and regression tests. Shared-fact check confirmed two conflicts in the main sample. The independent sample produced duplicate-settlement counterexamples.
- 17.5. Majority voting with distinct prompts, confidence and post-vote quote verification. Early three-vote ablation scored 12/30 recall. The selected report uses one vote for higher measured recall.
- 17.6 and 17.7. Fintech and API checks with verified quotes and scoped regression tests. The selected report includes domain and API findings.
- 17.2, 17.3 and 17.4. Gherkin from resolved scenarios, coverage gaps, proposed requirement diffs with follow-up fixes, and a source-linked traceability table. Test and diff sections are visible through the UI report.
- 17.8. Per-requirement score, observed ISO criteria and HTML readiness charts.
- 17.9. Source quote highlights, answers and rechecks, separate QA tabs, responsive light/dark workspace.
- 17.10. JSONL agent trace, request digests, response counts, timing, provider tokens and cache hits. Trace is also available in the web UI. Browser verification passed source highlights, Q&A and the three QA views (offline path).
- 17.12. Jira CSV/JSON and DOCX exports tested through the CLI. Added a PR workflow for spec changes. GitHub runner not exercised.
- 17.13. Version diff matches moved evidence and retains duplicate occurrences; supports source documents or generated JSON reports.
- 9 and 17.11. Final sample exceeds the 75% recall target. The benchmark lists the seven missed groups and reports ablation counts bound to the committed report hash.
- Final report uses 20 cached Qwen responses and includes 66 requirements, 100 findings, eight generated QA cases and two simulator counterexamples. Separate cold run ran in 249.52 seconds with 19 live calls and no failed checks.
- Final verification: 41 offline tests in a clean venv, PDF fallback, full-model SSE API, browser Q&A and highlights, export/diff smoke checks, workflow YAML and Bash syntax, and secret-prefix history scan. Gemini runtime, hosted GitHub Actions and visual DOCX rendering remain unverified.
- 18. Gemini is now the default (`gemini-3.8-flash`, verified on ai.google.dev models page 2026-11-27); `.env.example` needs only GEMINI_API_KEY. 429/5xx retried up to REQCHECK_MAX_RETRIES with Retry-After or 2/4/8 s backoff; REQCHECK_CONCURRENCY (2 on Gemini). ConnectError, 401/403/404 or invalid key stop all further calls (1 request instead of 47 on the offline PDF run). Passport shows successful responses and the reason the model was unavailable. Old report JSON still loads.
- 19. Verdict states «Начинать разработку / тестирование» with critical and major requirement IDs; first fixes skip repeated quotes (five distinct defects on the sample). 43 offline tests pass (web tests need fastapi, not installable in that sandbox). Committed reports/ left as generated at 6f4e3d1; regenerate with Gemini for submission.
- 20. Clarifier groups findings by complete linkage on cited quotes (Jaccard >= 0.5) so a shared context line cannot chain topics; primary finding leads unless its question is rhetorical; other wordings kept as `related` («Также:») in MD and web UI. Saved report: 99 questions -> 66, all 99 wordings kept; «Аналитик» share 78% -> 50%. Routing by criterion, question and quotes. `--interactive` asks top REQCHECK_INTERACTIVE_LIMIT (8). Report states question count, blocking questions, Russian plurals.
- 21. `reqcheck/structure.py`: both rules hit G27 and G30 on MD and PDF with verified quotes; 0 findings on merchant-settlement (generality check). Expected recall after the next full run: 25/30 if LLM findings hold; must be re-adjudicated (eval binds to report hash). 50 offline tests. Remaining LLM-only misses: G14, G15, G20, G21, G23 — prompt work needs a live model to evaluate, not attempted blind.
- Night-run verification: regenerated the report at 1b1ec93 with 20 cached Qwen responses. Verified every citation on both specs. Matched G27 and G30 in the refreshed report. Main sample: 102 findings and 67 questions. Independent sample: 43 findings and 18 questions. 53 offline tests pass.
- Jury workbench: selected finding links directly to its question. The submit button stays visible and the server-confirmed answer count is shown after recheck. Tested D-101 → Q-06 in Edge with six live local responses, four follow-up findings and no failed stage. PDF CLI run: 66 requirements, 100 findings, 19 live requests, 252 seconds; every citation verified.
- Jury recording: docs/demo.mp4 (2:46.52), Russian narration and selectable Russian subtitles. Covers both source rules, a real answer/recheck, agent trace, QA, verdict and benchmark. README and docs/demo.md link the deliverables.
