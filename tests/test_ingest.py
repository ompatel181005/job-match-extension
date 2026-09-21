from job_matcher.ingest import parse_markdown_resume
from job_matcher.models import EvidenceSection, MarkdownResumeRequest


def test_markdown_ids_are_stable() -> None:
    request = MarkdownResumeRequest(
        id="data-base",
        name="Data Base",
        markdown="## Projects\n- Built an ETL pipeline.\n## Skills\nPython, SQL",
    )

    first = parse_markdown_resume(request)
    second = parse_markdown_resume(request)

    assert first == second
    assert [item.section for item in first.evidence] == [
        EvidenceSection.PROJECT,
        EvidenceSection.SKILLS,
    ]
