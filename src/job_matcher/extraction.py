import hashlib
import re

from job_matcher.models import (
    JobExtractRequest,
    JobExtractResponse,
    Requirement,
    RequirementPriority,
)
from job_matcher.scoring import normalize

EXTRACTOR_VERSION = "deterministic-v1"
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")

# Seeded from JobFit's vocabulary, then grouped so aliases become one requirement.
SKILL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("python",),
    ("java",),
    ("javascript", "js"),
    ("typescript", "ts"),
    ("c++",),
    ("c#",),
    ("go", "golang"),
    ("rust",),
    ("sql",),
    ("postgresql", "postgres"),
    ("mongodb",),
    ("redis",),
    ("fastapi",),
    ("flask",),
    ("django",),
    ("react", "react.js"),
    ("node.js", "nodejs"),
    ("aws", "amazon web services"),
    ("azure",),
    ("gcp", "google cloud"),
    ("docker",),
    ("kubernetes", "k8s"),
    ("terraform",),
    ("spark", "pyspark"),
    ("kafka",),
    ("airflow",),
    ("dbt",),
    ("etl", "elt"),
    ("pytorch",),
    ("tensorflow",),
    ("scikit-learn", "sklearn"),
    ("computer vision", "cv"),
    ("model context protocol", "mcp"),
    ("rest", "restful"),
    ("graphql",),
    ("grpc",),
    ("ci/cd", "continuous integration", "continuous delivery"),
    ("linux",),
    ("git",),
)


def _has_phrase(text: str, phrase: str) -> bool:
    return f" {normalize(phrase)} " in f" {normalize(text)} "


def _priority(sentence: str) -> RequirementPriority:
    preferred_markers = ("preferred", "nice to have", "bonus", "ideally", "plus")
    return (
        RequirementPriority.PREFERRED
        if any(marker in sentence.casefold() for marker in preferred_markers)
        else RequirementPriority.REQUIRED
    )


def _weight(sentence: str) -> int:
    lowered = sentence.casefold()
    if any(marker in lowered for marker in ("must", "required", "minimum")):
        return 3
    if any(marker in lowered for marker in ("experience", "proficient", "strong")):
        return 2
    return 1


def _requirement_id(canonical: str) -> str:
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:10]
    return f"req-{normalize(canonical).replace(' ', '-')}-{digest}"


def extract_requirements(request: JobExtractRequest) -> JobExtractResponse:
    sentences = [part.strip(" -•\t") for part in SENTENCE_PATTERN.split(request.text)]
    sentences = [sentence for sentence in sentences if sentence]
    requirements: list[Requirement] = []

    for group in SKILL_GROUPS:
        matching_sentence = next(
            (
                sentence
                for sentence in sentences
                if any(_has_phrase(sentence, term) for term in group)
            ),
            None,
        )
        if not matching_sentence:
            continue
        canonical = group[0]
        requirements.append(
            Requirement(
                id=_requirement_id(canonical),
                text=matching_sentence[:500],
                keywords=[canonical],
                kind="skill",
                priority=_priority(matching_sentence),
                weight=_weight(matching_sentence),
            )
        )

    warnings: list[str] = []
    if not requirements:
        warnings.append(
            "No known technical requirements were detected; paste a fuller description or use AI extraction."
        )
    return JobExtractResponse(
        requirements=requirements,
        extractor_version=EXTRACTOR_VERSION,
        warnings=warnings,
    )
