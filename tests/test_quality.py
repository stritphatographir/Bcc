from reqcheck.findings import Evidence, Finding
from reqcheck.loader import Source
from reqcheck.quality import score_quality
from reqcheck.segmenter import Requirement


def test_readiness_uses_severity_and_marks_partial_review():
    source = Source(locator="1", text="Ответить быстро.")
    requirement = Requirement(id="R-01", document_id=None, source=source, quote=source.text)
    defect = Finding(code="weak", criterion="Проверяемость", severity="critical",
                     evidence=[Evidence(locator="1", quote=source.text)], requirements=[requirement.id],
                     explanation="Нет срока.", fix="Указать срок.", question="Какой срок?")
    critical = score_quality([requirement], [defect, defect], ["Контракты"])
    assert critical.readiness == "blocked"
    assert critical.requirements["R-01"] == 60
    assert critical.affected_criteria["Проверяемость"] == 1
    assert score_quality([requirement], [], ["Контракты"]).readiness == "incomplete"
