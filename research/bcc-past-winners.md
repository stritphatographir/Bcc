# Past Hackathons by BCC, BCC-HUB, and Partners

This document collects verified public records of hackathons organized or partnered by Bank CenterCredit (BCC), BCC Hub, Maqsut Narikbayev University (MNU), mnu.ai.club, SHAI.PRO, and Alpha Edu.

## Table of Hackathons

| Name | Year | Theme | Winners | What They Built | Source URL |
|---|---|---|---|---|---|
| **BCC Innovation Challenge** | 2017 | FinTech, Alternative Scoring, Smart Bots, Blockchain | 1. **GeForce**<br>2. **Vaco.kz**<br>3. **CodeWibe**<br>4. **InvestGamers** | Alternative credit scoring using digital footprint/social data; automated advisory bots; InvestGamers created an integration concept for mutual investment funds (ПИФ) and cryptocurrency/blockchain. | [kursiv.media](https://kursiv.media/2017-10-18/bank-tsentrkredit-podvel-itogi-finteh-hakatona/), [bcc.kz](https://www.bcc.kz/) |
| **Decentrathon 4.0 (AI Track by BCC & BCC Hub)** | 2025 | Practical Enterprise AI & FinTech: Personalized Push Notifications & Intelligent OCR 2.0 | **Push Case:**<br>1. **2.08** (Astana)<br>2. **yerayal** (Semey)<br>3. **Artificial spirit** (Almaty)<br><br>**OCR 2.0 Case:**<br>1. **StarWars** (Almaty)<br>2. **zhurttyn baldary** (Almaty)<br>3. **qwerty12345** (Astana) | **Push:** ML models for personalized push targeting, CTR optimization, and customer timing prediction.<br>**OCR 2.0:** Multimodal document processing, key-value entity extraction, and validation pipelines for complex bank forms. | [astanahub.com](https://astanahub.com/ru/article/stali-izvestny-imena-pobeditelei-krupneishego-khakatona-decentrathon-4-0), [digitalbusiness.kz](https://digitalbusiness.kz/) |
| **AI-Hackathon by SHAI.PRO** | 2025 | Autonomous AI Agents for Enterprise Workflows (Finance, Education, Industry, Gov) | Finalist teams honored at the "Leaders in AI" forum (21M KZT prize fund) | Autonomous corporate AI agents built on top of the SHAI.PRO enterprise platform for automating business document review and operational workflows. | [el.kz](https://el.kz/), [newsroom.kz](https://newsroom.kz/), [shai.pro](https://shai.pro/) |
| **BCC-HUB x MNU FinTech Hackathon** | 2025/2026 | AI Agent for Technical Requirements & PRD Quality Analysis | 12 Finalist teams compete for 1.8M KZT across 3 main nominations: *Best Business Value*, *Best Architecture*, *Best Presentation*. | Multi-agent pipelines for automated parsing, defect detection (ISO 29148 / IEEE 830), interactive clarification, and verification of FinTech specifications. | [bcchubagents.mnu.kz](https://bcchubagents.mnu.kz/), [mnu.kz](https://mnu.kz/), [astanahub.com](https://astanahub.com/ru/article/bcc-hub-x-mnu-fintech-hackathon) |

---

## Patterns

Judges at BCC, BCC Hub (led by Ruslan Yensebayev), MNU, and partner platforms reward specific technical and presentation patterns:

1. **Direct integration with bank workflows (High Business Value):** Solutions must solve practical bottlenecks in the bank SDLC or digital customer channels rather than present abstract academic exercises.
2. **Hybrid architecture (Deterministic rules + LLM critics):** Successful entries combine deterministic linters (lexicon, regex, schema checkers) with LLM agents. Pure generative approaches without guardrails suffer from hallucinations.
3. **Multi-agent modular design:** High scores for architecture (25% weight at MNU) reward clear separation of concerns: loader -> segmenter -> domain critics -> evidence verifier -> reporter.
4. **Interactive requirements clarification:** The primary differentiator in requirements engineering (25% weight) is generating precise, prioritized questions for business analysts to eliminate specification ambiguity.
5. **Exact evidence traceability:** For compliance and auditing in financial systems, judges reject ungrounded assertions. Every reported finding must cite line numbers, section paths, and verbatim source quotes.
6. **Graceful degradation and offline resilience:** Winning prototypes support multiple providers (OpenAI, local models like Qwen/vLLM) and provide linter-only fallback when external APIs fail.
7. **Clean CLI and API interfaces:** Teams that deliver reproducible single-command execution (`python -m <package> <input> -o <report>`) with structured JSON/Markdown outputs receive higher technical ratings.
8. **Quantified business ROI:** Winning presentations frame technical metrics in business terms: reduction in development rework, saved analyst hours, and error prevention before production.
9. **Working live demo over slide decks:** Live interactive execution showing the agent processing real specifications beats static mockups during jury evaluation.
10. **Strict data security and privacy posture:** Enterprise banking judges strictly penalize hardcoded credentials, data leakage, and unvetted cloud dependencies.

---

## Unknowns

1. **Source repositories for Decentrathon 4.0 winners:** Exact GitHub repositories for teams `StarWars`, `2.08`, and `zhurttyn baldary` are kept in private competition submissions or internal employer archives.
2. **Individual scores per rubric item:** Public press releases from Astana Hub and BCC state winners and prize amounts, but do not disclose itemized score breakdowns.
3. **Specific model weights used by winners:** Details regarding specific fine-tunes or proprietary prompt templates used by past winners remain unpublished proprietary data.
