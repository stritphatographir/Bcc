# Golden defects for examples/requirements.md

Expert list for measuring recall. Do NOT copy these into prompts or code: the agent must find them on its own.
Each item: id, place, defect. A finding counts as a hit when it points to the same place and the same defect.

## Contradictions (critical)

- G01. Ф-3 vs Ф-4. "максимум один такой push за календарный месяц" vs "следующее достижение вызывает push независимо от истории предыдущей настройки": after a threshold change in the same month, rules conflict.
- G02. Ф-2 vs acceptance criterion row 2. Month is defined by the purchase date ("по дате совершения покупки"), purchase made 31 Jan 23:58, but the expected result is the February counter.
- G03. Part B "Description": "Сохранение порога. Функциональные требования: чтение порога": save vs read conflict; no read method is specified although Part A says the app "читает и сохраняет" settings.
- G04. Part B REST type GET for a state-changing save; parameters (cardId, amount) in the query string; curl uses -G.
- G05. Part B Content-Type `application/json` while "Тело не используется".
- G06. Part B status 200 can return `"result":"ERROR"` while 400 is for invalid parameters: which code for an out-of-range amount is ambiguous; logic step 5 conflicts with 400.
- G07. Part B section 403 says a foreign card returns 404; 404 is not in the status list; 403 is described but never returned.
- G08. Part B "Если результат 200 или 201 — успешный" and heading "200. Successful — Created", but 201 is never described.
- G09. Types: request `amount`/`enabled` are integer, response `amount`/`enabled` are string.
- G10. Units: data requirements store purchase sum in тиын and threshold in тенге; API threshold in тенге; push sum unit not defined.
- G11. Goal says "в момент покупки", NFR says "в течение минуты".
- G12. Component names differ: "сервис настроек" / "хранилище настроек", "учёт расходов" / "сервис расходов".

## Incomplete or ambiguous (major)

- G13. Ф-2: "проведённые покупки" (posted) vs "дата совершения" (authorization date): event and status undefined; partial refunds, refunds into a closed month, whether a refund can re-trigger a push are undefined.
- G14. Ф-1: only "активной карты KZT": behavior for non-KZT cards, foreign-currency purchases on a KZT card, card blocked or reissued, additional cards / several cards per client undefined.
- G15. Ф-1: default threshold value undefined (only "уведомление выключено" by default).
- G16. Ф-3/Ф-4: enabling the alert or lowering the threshold when spending is already at or above the threshold: push or not is undefined.
- G17. NFR: "в течение минуты после получения события": which event, percentile, load; other NFR categories missing (availability, security, logging, monitoring, retention).
- G18. Integration idempotency "сохраняет исходный итог": idempotency key, out-of-order events, refund before purchase undefined.
- G19. Push content: text template, localization, delivery failure and retry, meaning of "признак отправки" (sent vs delivered) undefined.
- G20. UI: error message texts, validation rules, disabled state, when "сумма за месяц" refreshes are undefined.
- G21. Part B logic: whether `amount` is required and validated when `enabled=0` is undefined.
- G22. Part B: Prod URL "—", Swagger "—"; cardId format and whether it is a token or PAN undefined; rate limiting absent.
- G23. Data requirements: no `enabled` flag (Part B has DB field `enabled`), no currency, no retention or PII handling.

## Process and traceability (major/minor)

- G24. "Тестирование требований: заполняются тестировщиками": empty section.
- G25. Acceptance criteria cover only 3 scenarios: no criteria for refunds, threshold change, once-per-month push, enable/disable, boundaries 1 000 and 1 000 000, API errors.
- G26. Review checklist not filled; document version and date missing; approvers block empty; no JIRA link; no rollback plan.
- G27. BPMN and sequence diagram show only the happy path: no branches for refund, disabled alert, push already sent.
- G28. Goal has no measurable success metric.
- G29. Security: last four card digits and amount in push (lock-screen exposure), card id in query string logs.
- G30. Part B "Особые правила" 3 duplicates Ф-4 (design/requirement duplication, modifiability).
