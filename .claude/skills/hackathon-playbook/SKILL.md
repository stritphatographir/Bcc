---
name: hackathon-playbook
description: Winning rules for the BCC-HUB x MNU requirements-validator hackathon. Use before any work on the report format, clarifying questions, architecture docs, README, demo script, slides or pitch in this repo.
---

# Hackathon playbook (BCC-HUB x MNU, 2026)

Sources: `research/winning-playbook.md`, `research/bcc-past-winners.md`. Jury: 4 criteria, 25% each.

## Jury DNA (what BCC rewards)

- Practical bank workflow, not an academic exercise. BCC's 2025 Decentrathon AI track had a "personalized push notifications" case: the jury knows push/card-alert domain well. Our sample spec is a card-spend push alert. Speak their domain: тенге/тиын, idempotency, card token vs PAN, refunds, posting vs authorization.
- Working live product beats slides.
- Security posture matters to bank jurors: no secrets in git, local-model option for confidential specs.

## 1. Уточнение (clarifying questions)

- Clarifier output is a first-class report section, placed right after the summary. Also shown in the UI and in `--interactive`.
- Each question: ID, addressee role (бизнес-владелец, аналитик, архитектор, ИБ, QA), priority, linked finding IDs, exact quote, and 2-3 answer options when possible.
  Good: "Ф-2 считает месяц по дате совершения, а критерий приёмки №2 ждёт февральский счётчик для покупки 31 января. Какое правило верно: дата совершения или дата проведения?"
  Bad: "Уточните раздел 2."
- Interactive mode: ask the top critical questions, take answers, re-check affected requirements, log Q&A in the report.

## 2. Архитектура

- Show named agents with one job each and typed handoffs: Loader, Segmenter, Rule Linter, Requirement Critic, Set Critic, Evidence Verifier, Clarifier, Reporter, Orchestrator.
- Show it working: stage logs in the CLI, stage progress in the UI, a Mermaid diagram in the README.
- The Evidence Verifier is the signature feature. Log and report how many findings it dropped or repaired.
- Never a single big prompt. Provider-agnostic (any OpenAI-compatible endpoint, local model works).

## 3. Ценность

- Report must be usable by an analyst directly: severity, exact quote, standard clause, why, a rewritten requirement.
- Verdict answers "can dev and testing start" with the top fixes in order.
- Linter-only fallback when the LLM is down, marked in the passport.
- Numbers in README/slides: only ones we measured (runtime, number of findings, recall on our golden set, verifier drops). Boehm & Basili 2001 cost-of-change curve may be cited as published research. Never invent figures like "16 hours to 4 minutes".

## 4. Презентация и защита

- Demo video 3 min: 0:00 pain + hook (25s), 0:25 live run with stage logs (50s), 1:15 findings + clarifying questions + interactive answer (50s), 2:05 architecture + verifier drop (35s), 2:40 measured value + repo link (20s). No team bios at the start.
- Finals pitch 5 min: problem, live run, clarifier deep-dive, architecture, integration into the bank SDLC (CI gate for specs, Confluence/Jira) and security.
- Prepare defense answers: hallucinations (verifier), other documents (no hardcoding; second sample spec), confidential data (local model), cost (free-tier model), why not one prompt.

## Don't

- Generic findings without a quote and locator.
- Document-specific facts in prompts or code.
- Claims that the demo cannot back.
- Dependence on one cloud API during a live demo: keep a cached run ready.
