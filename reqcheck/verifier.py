import re

from .findings import Evidence, Finding
from .loader import Source


def match_evidence(evidence: Evidence, by_locator: dict[str, str]) -> Evidence | None:
    words = evidence.quote.split()
    source = by_locator.get(evidence.locator)
    if not words or source is None:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    match = re.search(pattern, source)
    if match:
        return evidence.model_copy(update={"quote": match[0]})
    return None


def verify(findings: list[Finding], sources: list[Source]) -> tuple[list[Finding], int]:
    by_locator = {source.locator: source.text for source in sources}
    accepted = []
    dropped = 0
    for finding in findings:
        verified = []
        for evidence in finding.evidence:
            match = match_evidence(evidence, by_locator)
            if match is None:
                break
            verified.append(match)
        else:
            accepted.append(finding.model_copy(update={"evidence": verified}))
            continue
        dropped += 1
    return accepted, dropped
