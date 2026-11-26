import re
from dataclasses import dataclass

from .findings import Evidence, Finding
from .loader import Source
from .segmenter import Requirement

MONEY = r"тенге|тиын|\bKZT\b|валют|эквайринг|плат[её]ж|выплат|банковск|карточн"


@dataclass(frozen=True)
class Check:
    code: str
    trigger: str
    specified: str
    gap: str
    fix: str
    question: str
    stakeholder: str = "Аналитик"


CHECKS = (
    Check("money-rounding", r"конверт|курс валют|вычетом комисс|процент от суммы",
          r"округл|round(?:ing)?|half.to.even|half.up",
          "Расчёт денежной суммы указан без правила округления.",
          "Задать единицу суммы, точность, момент и правило округления.",
          "До какой единицы и по какому правилу округляется результат расчёта?"),
    Check("currency-basis", r"конверт|курс валют|иностранн\w+ валют",
          r"курс.{0,45}(?:дат|времен|нацбанк|бирж)|(?:дат|времен).{0,45}курс",
          "Для конвертации не задана привязка курса к источнику или моменту.",
          "Указать источник, тип курса и дату или время, на которое берётся курс.",
          "Какой курс применяется, на какой момент и из какого источника?"),
    Check("idempotency-key", r"идемпотент|дубликат|повторн\w+\s+(?:доставк|событи|инструкц|событий)",
          r"(?:ключ|идентификатор)\s+(?:идемпотент|дедупликац)|idempotency[-_ ]key",
          "Повторная обработка описана без ключа идемпотентности и области его действия.",
          "Указать поля ключа, срок хранения и результат повторной обработки.",
          "Какие поля однозначно связывают повтор с исходной операцией?"),
    Check("event-order", r"возврат|сторнирован|reversal|refund",
          r"до\s+(?:получения\s+)?(?:исходной|оригинальн|первичной)|"
          r"(?:нет|отсутствует|не найдена)\s+(?:исходная|первичная)|вне порядк|out.of.order",
          "Для возврата или сторно отсутствует обработка события, пришедшего раньше исходной операции.",
          "Задать поведение при отсутствии исходной операции и повторе корректировки.",
          "Что делает система, если возврат пришёл до исходной операции?"),
    Check("business-calendar", r"рабочи\w*\s+(?:день|дн)|операционн\w*\s+(?:день|дн)|cut.off",
          r"календар.*(?:рабоч|празд|график)|(?:график|реестр).*календар|business.?calendar",
          "Срок зависит от рабочего или операционного дня. Источник календаря не указан.",
          "Указать календарь, часовой пояс, праздники и правило переноса срока.",
          "Какой календарь определяет рабочие дни и время переноса операции?"),
    Check("payment-audit", r"плат[её]жн\w+\s+поручени|проводк|перечислени\w*\s+средств",
          r"аудит|audit\s+log|журнал\s+(?:изменен|операци|событи)",
          "Для изменения или отправки денежной операции не описан журнал аудита.",
          "Задать обязательные поля журнала и события создания, отмены и повтора.",
          "Какие события и идентификаторы нужны для проверки истории денежной операции?", "Безопасность"),
    Check("card-data-exposure",
          r"(?:push|уведомлен).*(?:цифр|номер).{0,24}карт|(?:цифр|номер).{0,24}карт.*(?:push|уведомлен)",
          r"экран\w*\s+блокиров|lock.screen|маскир.*уведомлен",
          "Данные карты в уведомлении могут быть видны на заблокированном экране.",
          "Указать, какие данные видны на заблокированном экране и после входа.",
          "Какие сведения о карте и операции допускаются на заблокированном экране?", "Безопасность"),
)


def review_fintech(sources: list[Source], requirements: list[Requirement]) -> list[Finding]:
    text = "\n".join(source.text for source in sources)
    if not re.search(MONEY, text, re.I):
        return []
    findings = []
    for check in CHECKS:
        if re.search(check.specified, text, re.I):
            continue
        source = next((s for s in sources if not s.heading and re.search(check.trigger, s.text, re.I)), None)
        if source is None:
            continue
        findings.append(Finding(
            code=check.code, criterion="Полнота", severity="major",
            evidence=[Evidence(locator=source.locator, quote=source.text)],
            explanation=check.gap, fix=check.fix, question=check.question,
            stakeholder=check.stakeholder, agent="fintech",
            requirements=[r.id for r in requirements if r.source.locator == source.locator],
        ))
    return findings
