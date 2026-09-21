import hashlib
import re

from job_matcher.models import (
    EvidenceSection,
    MarkdownResumeRequest,
    ResumeDocument,
    ResumeEvidence,
)

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BULLET_PATTERN = re.compile(r"^(?:[-*+]\s+|[•‣▪]\s*)(.+?)\s*$")


def _section_from_heading(heading: str) -> EvidenceSection:
    lowered = heading.casefold()
    if any(word in lowered for word in ("experience", "employment", "work")):
        return EvidenceSection.EXPERIENCE
    if "project" in lowered:
        return EvidenceSection.PROJECT
    if any(word in lowered for word in ("skill", "technology", "technical")):
        return EvidenceSection.SKILLS
    return EvidenceSection.OTHER


def _evidence_id(resume_id: str, section: EvidenceSection, text: str) -> str:
    digest = hashlib.sha256(f"{resume_id}\0{section}\0{text}".encode()).hexdigest()[:12]
    return f"{resume_id}-{digest}"


def parse_markdown_resume(request: MarkdownResumeRequest) -> ResumeDocument:
    current_section = EvidenceSection.OTHER
    evidence: list[ResumeEvidence] = []

    for raw_line in request.markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = HEADING_PATTERN.match(line)
        if heading:
            # H1 is the document title; H3/H4 are employers, roles, or projects.
            # Only H2 headings define resume sections.
            if len(heading.group(1)) == 2:
                current_section = _section_from_heading(heading.group(2))
            continue
        bullet = BULLET_PATTERN.match(line)
        if bullet:
            text = bullet.group(1).strip()
        elif current_section == EvidenceSection.SKILLS:
            text = line.strip("*_` ")
        else:
            continue
        if text:
            evidence.append(
                ResumeEvidence(
                    id=_evidence_id(request.id, current_section, text),
                    section=current_section,
                    text=text,
                )
            )

    if not evidence:
        raise ValueError("resume Markdown must contain at least one bullet or skills line")
    return ResumeDocument(
        id=request.id,
        name=request.name,
        role_family=request.role_family,
        evidence=evidence,
    )
