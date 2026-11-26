import re

from .findings import Finding
from .loader import Source


def verify(findings: list[Finding], sources: list[Source]) -> tuple[list[Finding], int]:
    by_locator = {source.locator: source.text for source in sources}
    accepted = []
    dropped = 0
    for finding in findings:
        verified = []
        for evidence in finding.evidence:
            words = evidence.quote.split()
            if not words or evidence.locator not in by_locator:
                break
            pattern = r"\s+".join(re.escape(word) for word in words)
            match = re.search(pattern, by_locator[evidence.locator])
            if not match:
                break
            verified.append(evidence.model_copy(update={"quote": match[0]}))
        else:
            accepted.append(finding.model_copy(update={"evidence": verified}))
            continue
        dropped += 1
    return accepted, dropped
