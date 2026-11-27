# Golden defects for examples/merchant-settlement.md

Expert list for measuring recall. Do NOT copy these into prompts or code: the agent must find them on its own.
Each item: id, place, defect. A finding counts as a hit when it points to the same place and the same defect.

## Contradictions (critical)

- G01. BR-2 vs BR-3 vs AC-1. The 17:00 bank deadline makes it impossible to send the once-daily payout with an operation accepted at 17:40, even though the cutoff is 18:00 and AC-1 requires same-day dispatch.
- G02. BR-6 vs AC-3. BR-6 automatically cancels the repeat without an operator, but AC-3 requires operator approval and doubles the payout.
- G03. BR-5 and AC-4 vs §3 "Курс конвертации". The rule and example use the operation date, but the calculation table uses the calculation date, which can be a different day.

## Ambiguity, completeness and verifiability

- G04. BR-1, BR-2, BR-3 and AC-2. "операционный день", "рабочего дня", and "текущих суток" have no defined relationship or authoritative calendar, so eligibility and dispatch on working Sundays or holidays cannot be derived.
- G05. BR-3 "до 18:00 времени Астаны". It does not explicitly state whether an operation timestamped exactly 18:00 is included.
- G06. BR-3 "до 18:00 времени Астаны текущих суток". There is no assignment rule for operations accepted after the cutoff, so the next eligible payout and protection against omission are undefined.
- G07. BR-1 "с положительным остатком к выплате" and BR-4. The disposition of a negative balance is unspecified, including whether the deficit reduces a later payout.
- G08. BR-4 and §3 "Оборот дня | Шлюз эквайринга". The eligible transaction statuses and whether the turnover feed is gross or already net of refunds or fees are unspecified, risking omission or double subtraction.
- G09. BR-4 and §3 "Комиссия | Тарифный план". The commission rule lacks the applicable tariff version or effective date and does not say whether to calculate fees per operation or on aggregate turnover.
- G10. BR-4, BR-7 and §3. Refunds reduce the payout but the calculation data table has no refund field, source, or precision.
- G11. BR-5 "конвертируются по курсу Нацбанка". The target currency is not explicitly specified.
- G12. BR-5 and §3 "Курс конвертации". For a payout aggregating operations on different dates or in different currencies, the spec does not say how to apply each rate and combine the amounts.
- G13. BR-5 and §3 "Курс конвертации". There is no fallback or hold rule for an unavailable rate on the required date.
- G14. §3 "2 знака" and "4 знака". Precision is listed without the rounding method or the step at which rounding is applied.
- G15. BR-6 "на ту же сумму и ту же точку" and "в тот же день". No stable instruction ID or retry key distinguishes a duplicate from a legitimate instruction with the same attributes, and an otherwise identical retry after midnight falls outside the rule.
- G16. BR-2 "отправляется в банк". The spec does not define what to do if the bank rejects the instruction or its response is lost, including how to retry without paying twice.
- G17. BR-7 "после формирования выплаты". The rule does not define the treatment of a refund arriving at the moment of formation or the ordering rule when both events share a timestamp.
- G18. BR-7 "переносятся в следующую выплату" and BR-1. No carry-forward rule covers a refund for a merchant that has no positive payable balance in the immediately following cycle.
- G19. BR-1, BR-4 and §3 monetary fields. Monetary scale is listed, but currencies or unit conventions for turnover, commission and payout are not defined, so it is unclear which values can be subtracted directly.
- G20. AC-1 and AC-2. The fixtures specify acceptance time and expected dispatch but omit the positive payable balance precondition from BR-1.
- G21. BR-1 "формируются один раз" and BR-2 "отправляется в банк". The spec does not define recovery and reconciliation when generation completes but the system stops before recording or sending the instruction.
