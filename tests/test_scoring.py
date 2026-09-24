from job_matcher.models import (
    CoverageVerdict,
    EvidenceSection,
    RankRequest,
    Requirement,
    RequirementPriority,
    ResumeDocument,
    ResumeEvidence,
)
from job_matcher.scoring import rank_resumes


def evidence(evidence_id: str, section: EvidenceSection, text: str) -> ResumeEvidence:
    return ResumeEvidence(id=evidence_id, section=section, text=text)


def test_ranks_bullet_evidence_above_skills_only_evidence() -> None:
    requirement = Requirement(
        id="python-api",
        text="Build Python APIs",
        keywords=["Python", "FastAPI"],
        priority=RequirementPriority.REQUIRED,
        weight=3,
    )
    demonstrated = ResumeDocument(
        id="backend",
        name="Backend Base",
        evidence=[
            evidence("b1", EvidenceSection.EXPERIENCE, "Built Python services with FastAPI."),
        ],
    )
    listed = ResumeDocument(
        id="general",
        name="General Base",
        evidence=[
            evidence("s1", EvidenceSection.SKILLS, "Languages: Python; Frameworks: FastAPI"),
        ],
    )

    response = rank_resumes(RankRequest(requirements=[requirement], resumes=[listed, demonstrated]))

    assert [match.resume_id for match in response.matches] == ["backend", "general"]
    assert response.matches[0].score == 100
    assert response.matches[1].score == 60
    assert response.matches[0].coverage[0].verdict == CoverageVerdict.BULLET
    assert response.matches[1].coverage[0].verdict == CoverageVerdict.SKILLS_ONLY


def test_synonyms_match_and_missing_requirement_is_reported() -> None:
    requirements = [
        Requirement(id="pipeline", text="ETL pipelines", keywords=["ETL"]),
        Requirement(id="cloud", text="AWS", keywords=["AWS"]),
    ]
    resume = ResumeDocument(
        id="data",
        name="Data Base",
        evidence=[
            evidence("b1", EvidenceSection.PROJECT, "Designed ELT pipelines for analytics."),
        ],
    )

    match = rank_resumes(RankRequest(requirements=requirements, resumes=[resume])).matches[0]

    assert match.coverage[0].verdict == CoverageVerdict.BULLET
    assert match.coverage[0].matched_keywords == ["ETL"]
    assert match.coverage[1].verdict == CoverageVerdict.MISSING
    assert match.missing_requirement_ids == ["cloud"]


def test_ml_abbreviation_matches_full_requirement() -> None:
    requirement = Requirement(
        id="language-models",
        text="Experience with large language models",
        keywords=["large language models"],
    )
    resume = ResumeDocument(
        id="ai",
        name="AI Base",
        evidence=[evidence("b1", EvidenceSection.PROJECT, "Built an LLM evaluation system.")],
    )

    match = rank_resumes(RankRequest(requirements=[requirement], resumes=[resume])).matches[0]

    assert match.score == 100
    assert match.coverage[0].matched_keywords == ["large language models"]


def test_top_scores_within_threshold_are_marked_close() -> None:
    requirements = [Requirement(id="python", text="Python", keywords=["Python"])]
    first = ResumeDocument(
        id="a",
        name="A",
        evidence=[evidence("a1", EvidenceSection.EXPERIENCE, "Python")],
    )
    second = ResumeDocument(
        id="b",
        name="B",
        evidence=[evidence("b1", EvidenceSection.PROJECT, "Python")],
    )

    response = rank_resumes(RankRequest(requirements=requirements, resumes=[first, second]))

    assert response.close_match is True
    assert response.score_difference == 0
