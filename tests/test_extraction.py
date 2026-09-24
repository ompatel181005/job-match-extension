from job_matcher.extraction import extract_requirements
from job_matcher.gemini import GeminiExtractionError
from job_matcher.models import (
    JobExtractRequest,
    JobExtractResponse,
    Requirement,
    RequirementPriority,
)

GENESIS_EXCERPT = """
We are conducting fundamental research at the intersection of machine learning,
physics, and computational chemistry. You will design and build generative
foundation models at scale. Projects may involve diffusion models, large language
models, or reinforcement learning. Turn research ideas into high-quality code by
implementing and optimizing multi-modal models and algorithms. Applicants must be
enrolled in Computer Science, Machine Learning, or a related technical field.
"""


def test_offline_extractor_handles_ml_research_posting(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = extract_requirements(JobExtractRequest(text=GENESIS_EXCERPT))

    keywords = {item.keywords[0] for item in response.requirements}
    assert response.extractor_version == "deterministic-v2"
    assert {
        "machine learning",
        "computational chemistry",
        "foundation models",
        "diffusion models",
        "large language models",
        "reinforcement learning",
        "multimodal",
    } <= keywords
    assert response.warnings == []


def test_configured_gemini_provider_is_used(monkeypatch) -> None:
    expected = JobExtractResponse(
        requirements=[
            Requirement(
                id="req-research",
                text="Build generative models.",
                keywords=["generative models"],
                kind="responsibility",
                priority=RequirementPriority.REQUIRED,
                weight=3,
            )
        ],
        extractor_version="gemini:test-model",
    )

    def fake_extract(request, *, api_key, model):
        assert request.text == GENESIS_EXCERPT
        assert api_key == "test-key"
        assert model == "test-model"
        return expected

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr("job_matcher.extraction.extract_requirements_with_gemini", fake_extract)

    assert extract_requirements(JobExtractRequest(text=GENESIS_EXCERPT)) == expected


def test_gemini_failure_falls_back_offline(monkeypatch) -> None:
    def failed_extract(request, *, api_key, model):
        raise GeminiExtractionError("unavailable")

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("job_matcher.extraction.extract_requirements_with_gemini", failed_extract)

    response = extract_requirements(JobExtractRequest(text=GENESIS_EXCERPT))

    assert response.extractor_version == "deterministic-v2"
    assert response.requirements
    assert response.warnings[0] == "AI extraction failed; used the offline extractor."
