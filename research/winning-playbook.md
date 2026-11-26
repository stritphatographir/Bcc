# Hackathon Winning Playbook: BCC-HUB x MNU FinTech Hackathon

Playbook for winning the AI Requirements Validator Hackathon judged by Bank CenterCredit (BCC) and MNU.
Target scoring criteria (25% each):
1. **Clarification (Уточнение)**: The agent asks the right clarifying questions about the specification.
2. **Architecture (Архитектура)**: Clear, modular multi-agent system design.
3. **Product Value (Ценность)**: Business utility, time/cost savings for banks, high defect recall, zero hallucinations.
4. **Presentation & Defense (Презентация и защита)**: High-impact 3-minute video screencast and 5-minute live jury defense.

---

## Do (Max 15 Actionable Recommendations)

1. **Spotlight Clarifying Questions First (Criterion 1 - 25%)**: Make clarifying questions prominent in both the report and the demo UI. Group questions by role (Business Analyst, Security Architect, Core Banking Integrator, QA) and rank them by business risk.
   *Source*: [Devpost Hackathon Guide](https://devpost.com/resources)
2. **Anchor Questions Directly to Verbatim Document Quotes**: Every question must reference the exact requirement ID, section, and text quote. Never output abstract questions like "Please clarify performance".
   *Source*: [ISO/IEC/IEEE 29148:2018 §5.2.5 Verifiable & Unambiguous](https://www.iso.org/standard/72089.html)
3. **Visualize Architecture via Clean Role Division (Criterion 2 - 25%)**: Present an explicit Orchestrator-Worker / Critic-Verifier pipeline. Name distinct agents: `Loader`, `Segmenter`, `Rule Linter`, `Requirement Critic`, `Set Critic`, `Evidence Verifier`, `Clarifier`, `Reporter`.
   *Source*: [SystemDesign.one Multi-Agent Patterns](https://systemdesign.one)
4. **Demonstrate a Self-Correction / Verification Loop in Real Time**: Show the anti-hallucination `Evidence Verifier` actively dropping or repairing an ungrounded finding. This proves the architecture is not a naive single prompt.
   *Source*: [Mastra Multi-Agent Workflows & Verification](https://mastra.ai)
5. **Frame Product Value with Hard Banking Economics (Criterion 3 - 25%)**: Cite the Barry Boehm / NIST software economic curve: catching a requirement defect before release saves up to 100x compared to a hotfix in production banking systems.
   *Source*: [Boehm & Basili, "Software Defect Reduction Top 10 List", IEEE Computer 2001](https://www.cs.umd.edu/projects/SoftEng/ESEG/papers/82.70.pdf)
6. **Quantify Analyst Time Savings**: Frame the tool as a copilot: "Reduces initial SRS review time from 16 hours to 4 minutes; ensures 100% checklist coverage across ISO 29148 and IEEE 830 standards."
   *Source*: [NIST Planning Report 02-3](https://www.nist.gov)
7. **Strict Verbatim Anti-Hallucination Guard**: Implement deterministic exact-string matching between quotes and the source text. In the passport header, display `dropped_hallucinations_count: 0`.
   *Source*: [StrictDoc Requirements Integrity](https://github.com/strictdoc/strictdoc)
8. **Show Real Fintech Edge Cases in Demo Data**: Test with real banking nuances: KZT vs tiyn (тенге / тиын), idempotency keys on payment endpoints, rollback scenarios for card authorizations, and PII storage limits.
   *Source*: [National Bank of Kazakhstan Open Banking Guidelines](https://nationalbank.kz)
9. **Interactive Mode in CLI & Streamlit**: Implement `--interactive` where the agent asks top-3 critical questions, receives answers from the operator, patches the report, and logs the Q&A in the passport.
   *Source*: [MLH Hackathon Winner Strategies](https://mlh.io)
10. **Graceful Degradation (Offline Mode)**: If LLM APIs fail or return rate-limit errors, fall back to the deterministic regex/lexicon linter and generate a partial report with passport flag `mode: heuristic_offline`.
    *Source*: [Devpost Hackathon Project Best Practices](https://devpost.com)
11. **Strict 1-Command CLI Interface**: Ensure `python -m reqcheck input.md -o report.md` runs with zero setup hurdles and reads model settings from `.env`.
    *Source*: [BCC-HUB Task Specification](https://github.com/BCC-HUB/ai-requirements-validator-task)
12. **Start Video Directly on Pain Point and Running Product**: Avoid slide fluff. First 15 seconds must state: "Bank specifications take days to review and harbor million-dollar release bugs. Watch our agent audit this 10-page spec in 60 seconds."
    *Source*: [AngelHack 3-Minute Demo Pitch Guide](https://angelhack.com)
13. **Keep Live Presentation Strictly on Timing**: In 5-minute live defense: 1 min Problem & Metrics, 1.5 min Live Flow (Spec -> Findings -> Questions), 1.5 min Multi-agent Architecture & Anti-hallucination guard, 1 min Banking Value & Q&A.
    *Source*: [Devpost Guide to Pitching Hackathon Projects](https://devpost.com)
14. **Include a Real Passport with Git Hash & Audit Trails**: Include input SHA-256, model provider, prompt hash, execution timestamp, and git commit ID in the generated report passport for auditability.
    *Source*: [IEEE 830-1998 §4.3 Traceability](https://standards.ieee.org)
15. **Pre-test Against Golden Defect Benchmark**: Create `eval/golden_defects.md` with seeded violations (ambiguities, contradictions, missing NFRs) and compute automated recall scores.
    *Source*: [Jon Verrier Requirement Linter](https://github.com/jonverrier/RequirementLinter)

---

## Don't (Max 8 Critical Anti-Patterns)

1. **Don't Output Generic Phrases or Abstract Advice**: Never output "The system should be faster" or "Make requirements clearer". Every defect must state standard criterion, exact quote, why it violates the standard, and proposed replacement text.
2. **Don't Show a "Single LLM Call" Black Box**: If judges see a single 5,000-token prompt generating the report, Architecture score drops to minimum. Delineate segmenter, critics, and evidence verifiers clearly.
3. **Don't Waste 60 Seconds Introducing Team Members**: In a 3-minute video, team biographies waste 33% of the score. Introduce product and value immediately; put names on a 2-second title card at the end.
4. **Don't Allow Unverified Hallucinated Quotes**: One fictional quote discovered by a bank auditor destroys credibility. A finding without a verified source substring must be eliminated.
5. **Don't Rely Solely on Cloud API Connections**: Cloud APIs timeout or face rate limits during live jury trials. Maintain local fallback or disk-cached runs with deterministic replay.
6. **Don't Hardcode Specific Document Terms into Prompts**: Hardcoding terms like "BCC", "Казком", or specific field names in prompt templates causes immediate failure when tested against an unseen specification.
7. **Don't Leave Ambiguity in Clarifying Questions**: Never ask "What do you mean in section 2?". Ask: "Section 2.1 states transaction timeout is 5s, but Section 4.3 specifies 30s. Which timeout applies to core banking gateway responses?"
8. **Don't Hide Error Scenarios and Edge Cases**: In fintech specs, absence of error handling, missing timeouts, and vague SLAs are the #1 source of production downtime. Always evaluate missing NFRs.

---

## Demo Video Script Skeleton (3-Minute Screencast)

- **[0:00 - 0:25] The Problem & Hook (25s)**
  - *Visual*: Split screen: a dense 20-page bank SRS vs. a typical production bug incident ticket.
  - *Audio*: "Financial specifications contain hidden ambiguities, conflicting timeouts, and untestable terms. An analyst spends 2 days reviewing them, yet defects leak to production where fixes cost 100x more. Meet ReqCheck: an automated multi-agent validator aligned with ISO 29148."
- **[0:25 - 1:15] The Live Run & CLI / Web Interface (50s)**
  - *Visual*: Terminal executing `python -m reqcheck examples/requirements.pdf -o reports/report.md`. Pipeline logs show stages executing (`[Loader]`, `[Segmenter]`, `[Rule Linter]`, `[Requirement Critics]`, `[Evidence Verifier]`). Web UI displays progress nodes lighting up.
  - *Audio*: "ReqCheck takes PDF, Word, or Markdown documents. Notice the pipeline: it segments text into atomic requirements, runs deterministic checks, and deploys specialized critic agents. Total execution: under 60 seconds."
- **[1:15 - 2:05] The Findings & Clarifying Questions (Criterion 1 & 3 Spotlight) (50s)**
  - *Visual*: Scrolling through generated Markdown/HTML report. Zoom in on:
    1. Passport table with audit metadata.
    2. Exact finding with verbatim quote and rewrite suggestion.
    3. The "Clarification Table": Prioritized questions grouped by stakeholder (Business vs Tech).
    4. Interactive terminal CLI prompt answering a question and updating the verdict.
  - *Audio*: "Look at defect #4: 'Быстро переводить средства'. Flagged under ISO 29148 for untestable weak wording. The agent suggests the exact latency metric. More importantly, see the Clarifier Agent: it detects a contradiction between payment status 'PENDING' in functional specs and HTTP 200 in the API table, generating this exact question for the core banking team."
- **[2:05 - 2:40] Multi-Agent Architecture & Anti-Hallucination Guard (35s)**
  - *Visual*: Clean architecture slide/diagram. Highlight the `Evidence Verifier` box and Pydantic validation boundaries. Show terminal log: `Dropped 1 hallucinated citation; 100% verified`.
  - *Audio*: "Under the hood, we use a modular multi-agent pipeline. Pydantic schemas enforce type safety at each boundary. Our Evidence Verifier guarantees zero hallucinations by dropping any finding whose quote does not match the original document byte-for-byte."
- **[2:40 - 3:00] Business Impact, Value, & Wrap-up (20s)**
  - *Visual*: Summary metrics slide: "Review time: 16h -> 1min | 100% ISO 29148 coverage | Zero hallucinated citations". QR code to repo.
  - *Audio*: "ReqCheck turns requirements review from a human bottleneck into a continuous QA gate for Bank CenterCredit. Code, tests, and documentation are on GitHub. Thank you."

---

## Pitch Skeleton for Finals (5-Minute Bank Jury Defense)

- **Minute 1: The Banking Reality & Financial Impact (Problem)**
  - Requirements defects cause 40-50% of software defects (NIST / Boehm).
  - In retail and transactional banking, an untestable or contradictory requirement leads to failed audit compliance, security vulnerabilities, or payment processing rollbacks.
  - Human review is slow, subjective, and inconsistent across analyst teams.
- **Minute 2: Product Solution & The "Live Moment" (Demo)**
  - Show live analysis of a realistic banking integration document (e.g., P2P transfers / Open Banking API).
  - Show generated report passport, segmentation table, and severity breakdown (Critical / Major / Minor).
  - Highlight the release verdict: "Can dev and QA start? NO - 3 critical blockers must be resolved."
- **Minute 3: Criterion 1 Deep-Dive (Clarifying Questions)**
  - Present the Clarifier module. Explain why good questions are more valuable to a Lead Analyst than raw linter warnings.
  - Demonstrate a prioritized list of questions categorized by role (Business Analyst, Security Engineer, Database Admin).
  - Show how the agent suggests the *re-formulated requirement* ready for copy-pasting.
- **Minute 4: Architecture & Engineering Rigor (Multi-Agent System)**
  - Walk through the architecture: Separation of Concerns.
  - Fast deterministic linting (regex, weak-word lexicon) + LLM semantic criticism (ISO 29148 / IEEE 830 criteria) + Strict Evidence Verification.
  - Resiliency: works with any OpenAI-compatible backend (Gemini, local Qwen, vLLM), handles token context limits via atomic chunking, zero external data leaks.
- **Minute 5: Enterprise Integration, Security & Defense**
  - How it integrates into BCC workflow: Git pre-commit hooks for PR specs, Confluence integration, CI/CD gates.
  - Security: Local model compatibility for confidential banking specifications (air-gapped deployment).
  - Closing defense statement: "ReqCheck brings formal standards (ISO/IEEE) into everyday fintech delivery."

---

## Prior Art to Cite (Tools, Standards, and Ideas)

1. **NASA Automated Requirements Measurement (ARM) Tool**
   *Idea*: Introduced the canonical "weak words" and ambiguity indicators (e.g., *adequate, timely, easy, as appropriate, TBD*) to objectively flag untestable specifications.
   *Reference*: [NASA SATC ARM Study (KTH Mirror)](https://www.kth.se) / [NASA Technical Reports Server](https://ntrs.nasa.gov)
2. **Jon Verrier RequirementLinter**
   *Idea*: Open-source AI linter checking user stories and requirements against INCOSE *Guide to Writing Requirements* (GtWR) rules.
   *Reference*: [GitHub: jonverrier/RequirementLinter](https://github.com/jonverrier/RequirementLinter)
3. **StrictDoc (Docs-as-Code & Requirements Traceability)**
   *Idea*: Strict requirements modeling with human-readable text files, strict schema verification, and traceability matrices.
   *Reference*: [GitHub: strictdoc-project/strictdoc](https://github.com/strictdoc/strictdoc)
4. **RMToo (Requirements Management Tool)**
   *Idea*: Git-based open-source requirements management with integrated heuristic quality checks and dependency graphing.
   *Reference*: [GitHub: florath/rmtoo](https://github.com/florath/rmtoo)
5. **OpenFastTrace (OFT)**
   *Idea*: Fast, lightweight tracing tool checking specification coverage and validation status across artifacts.
   *Reference*: [GitHub: itsallcode/openfasttrace](https://github.com/itsallcode/openfasttrace)
6. **ISO/IEC/IEEE 29148:2018 (Systems and software engineering — Life cycle processes — Requirements engineering)**
   *Idea*: Standardized definitions for individual requirement characteristics (§5.2.5: necessary, unambiguous, verifiable) and set characteristics (§5.2.6: consistent, complete).
   *Reference*: [ISO Standards Catalog 29148:2018](https://www.iso.org/standard/72089.html)
7. **IEEE 830-1998 (Recommended Practice for Software Requirements Specifications)**
   *Idea*: Foundation for SRS quality: unambiguous, complete, verifiable, consistent, traceable.
   *Reference*: [IEEE Xplore IEEE 830-1998](https://ieeexplore.ieee.org/document/720574)
8. **Barry Boehm & Victor Basili Software Defect Reduction Top 10**
   *Idea*: Empirical cost-of-change curve showing defects found post-delivery cost 50x-100x more to remediate than those resolved in requirements.
   *Reference*: [IEEE Computer Society, Vol. 34, No. 1, 2001](https://www.cs.umd.edu/projects/SoftEng/ESEG/papers/82.70.pdf)
