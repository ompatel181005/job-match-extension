import re
from collections.abc import Iterable, Mapping

from job_matcher.models import (
    CoverageVerdict,
    EvidenceSection,
    RankRequest,
    RankResponse,
    Requirement,
    RequirementCoverage,
    RequirementPriority,
    ResumeDocument,
    ResumeEvidence,
    ResumeMatch,
)

SCORING_VERSION = "lexical-v1"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[.+#-][a-z0-9]+)*")

DEFAULT_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"etl", "elt"}),
    frozenset({"mcp", "model context protocol"}),
    frozenset({"cv", "computer vision"}),
    frozenset({"ml", "machine learning"}),
    frozenset({"generative ai", "generative artificial intelligence"}),
    frozenset({"foundation model", "foundation models"}),
    frozenset({"diffusion model", "diffusion models"}),
    frozenset({"large language model", "large language models", "llm", "llms"}),
    frozenset({"reinforcement learning", "rl"}),
    frozenset({"multimodal", "multi-modal"}),
    frozenset({"embedding", "embeddings", "vector embedding", "vector embeddings"}),
    frozenset({"js", "javascript"}),
    frozenset({"ts", "typescript"}),
    frozenset({"postgres", "postgresql"}),
    frozenset({"ci/cd", "continuous integration", "continuous delivery"}),
)


def normalize(value: str) -> str:
    """Normalize text for deterministic phrase matching."""
    return " ".join(TOKEN_PATTERN.findall(value.casefold()))


def build_synonym_map(
    groups: Iterable[Iterable[str]] = DEFAULT_SYNONYM_GROUPS,
) -> dict[str, frozenset[str]]:
    mapping: dict[str, frozenset[str]] = {}
    for group in groups:
        normalized = frozenset(normalize(term) for term in group)
        for term in normalized:
            mapping[term] = normalized
    return mapping


def phrase_present(phrase: str, text: str) -> bool:
    normalized_phrase = normalize(phrase)
    normalized_text = normalize(text)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_text} "


def keyword_present(keyword: str, text: str, synonyms: Mapping[str, frozenset[str]]) -> bool:
    normalized_keyword = normalize(keyword)
    candidates = synonyms.get(normalized_keyword, frozenset({normalized_keyword}))
    return any(phrase_present(candidate, text) for candidate in candidates)


def _placement(section: EvidenceSection) -> float:
    if section in {EvidenceSection.EXPERIENCE, EvidenceSection.PROJECT}:
        return 1.0
    if section == EvidenceSection.SKILLS:
        return 0.6
    return 0.8


def _coverage_for_evidence(
    requirement: Requirement,
    evidence: ResumeEvidence,
    synonyms: Mapping[str, frozenset[str]],
) -> tuple[float, list[str]]:
    matched = [
        keyword
        for keyword in requirement.keywords
        if keyword_present(keyword, evidence.text, synonyms)
    ]
    return len(matched) / len(requirement.keywords), matched


def score_requirement(
    requirement: Requirement,
    resume: ResumeDocument,
    synonyms: Mapping[str, frozenset[str]],
) -> RequirementCoverage:
    candidates: list[tuple[float, float, ResumeEvidence, list[str]]] = []
    for evidence in resume.evidence:
        raw_coverage, matched = _coverage_for_evidence(requirement, evidence, synonyms)
        candidates.append(
            (raw_coverage * _placement(evidence.section), raw_coverage, evidence, matched)
        )

    effective, raw_coverage, evidence, matched = max(candidates, key=lambda item: item[0])
    placement = _placement(evidence.section)

    if effective == 0:
        return RequirementCoverage(
            requirement_id=requirement.id,
            verdict=CoverageVerdict.MISSING,
            coverage=0,
            placement_multiplier=0,
            matched_keywords=[],
        )
    if raw_coverage < 1:
        verdict = CoverageVerdict.PARTIAL
    elif evidence.section == EvidenceSection.SKILLS:
        verdict = CoverageVerdict.SKILLS_ONLY
    else:
        verdict = CoverageVerdict.BULLET

    return RequirementCoverage(
        requirement_id=requirement.id,
        verdict=verdict,
        coverage=raw_coverage,
        placement_multiplier=placement,
        matched_keywords=matched,
        evidence_id=evidence.id,
        evidence_text=evidence.text,
    )


def score_resume(
    requirements: list[Requirement],
    resume: ResumeDocument,
    synonyms: Mapping[str, frozenset[str]],
) -> ResumeMatch:
    results = [score_requirement(requirement, resume, synonyms) for requirement in requirements]
    total_weight = 0.0
    earned = 0.0
    for requirement, coverage in zip(requirements, results, strict=True):
        priority_multiplier = 2 if requirement.priority == RequirementPriority.REQUIRED else 1
        effective_weight = requirement.weight * priority_multiplier
        total_weight += effective_weight
        earned += effective_weight * coverage.coverage * coverage.placement_multiplier

    missing = [
        result.requirement_id for result in results if result.verdict == CoverageVerdict.MISSING
    ]
    return ResumeMatch(
        resume_id=resume.id,
        resume_name=resume.name,
        role_family=resume.role_family,
        score=round(100 * earned / total_weight, 1),
        coverage=results,
        missing_requirement_ids=missing,
    )


def rank_resumes(request: RankRequest) -> RankResponse:
    synonyms = build_synonym_map()
    matches = sorted(
        (score_resume(request.requirements, resume, synonyms) for resume in request.resumes),
        key=lambda match: (-match.score, match.resume_name.casefold(), match.resume_id),
    )
    difference = round(matches[0].score - matches[1].score, 1) if len(matches) > 1 else None
    return RankResponse(
        matches=matches,
        close_match=difference is not None and difference <= request.close_score_threshold,
        score_difference=difference,
        scoring_version=SCORING_VERSION,
    )
