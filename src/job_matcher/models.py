from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class RequirementPriority(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class EvidenceSection(StrEnum):
    EXPERIENCE = "experience"
    PROJECT = "project"
    SKILLS = "skills"
    OTHER = "other"


class CoverageVerdict(StrEnum):
    BULLET = "covered_in_bullet"
    SKILLS_ONLY = "covered_in_skills_only"
    PARTIAL = "partially_covered"
    MISSING = "missing"


class Requirement(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)
    kind: str = "concept"
    priority: RequirementPriority = RequirementPriority.REQUIRED
    weight: int = Field(default=1, ge=1, le=3)


class ResumeEvidence(BaseModel):
    id: str = Field(min_length=1)
    section: EvidenceSection
    text: str = Field(min_length=1)


class ResumeDocument(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role_family: str | None = None
    evidence: list[ResumeEvidence] = Field(min_length=1)

    @model_validator(mode="after")
    def evidence_ids_are_unique(self) -> "ResumeDocument":
        ids = [item.id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence ids must be unique within a resume")
        return self


class RankRequest(BaseModel):
    requirements: list[Requirement] = Field(min_length=1)
    resumes: list[ResumeDocument] = Field(min_length=1)
    close_score_threshold: float = Field(default=3.0, ge=0, le=20)


class RequirementCoverage(BaseModel):
    requirement_id: str
    verdict: CoverageVerdict
    coverage: float = Field(ge=0, le=1)
    placement_multiplier: float = Field(ge=0, le=1)
    matched_keywords: list[str]
    evidence_id: str | None = None
    evidence_text: str | None = None


class ResumeMatch(BaseModel):
    resume_id: str
    resume_name: str
    role_family: str | None
    score: float = Field(ge=0, le=100)
    coverage: list[RequirementCoverage]
    missing_requirement_ids: list[str]


class RankResponse(BaseModel):
    matches: list[ResumeMatch]
    close_match: bool
    score_difference: float | None
    scoring_version: str


class MarkdownResumeRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role_family: str | None = None
    markdown: str = Field(min_length=1, max_length=200_000)


class JobExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)
    title: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=2_000)


class JobExtractResponse(BaseModel):
    requirements: list[Requirement]
    extractor_version: str
    warnings: list[str] = Field(default_factory=list)


class JobRankResponse(BaseModel):
    extraction: JobExtractResponse
    ranking: RankResponse
