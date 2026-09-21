import json
from pathlib import Path

from job_matcher.library import load_resume_library
from job_matcher.models import EvidenceSection


def write_resume(root: Path, role_family: str) -> None:
    directory = root / role_family
    directory.mkdir(parents=True)
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "id": f"{role_family}-id",
                "name": f"{role_family} base",
                "role_family": role_family,
                "updated_at": "2026-09-21T00:00:00Z",
            }
        )
    )
    (directory / "resume.md").write_text(
        "## Work Experience\n### Company\n#### Engineer\n- Built Python APIs.\n"
        "## Technical Skills\nPython, FastAPI\n"
    )


def test_loads_resume_library_and_preserves_section_across_subheadings(tmp_path: Path) -> None:
    write_resume(tmp_path, "backend")

    resumes = load_resume_library(tmp_path)

    assert len(resumes) == 1
    assert [item.section for item in resumes[0].evidence] == [
        EvidenceSection.EXPERIENCE,
        EvidenceSection.SKILLS,
    ]
