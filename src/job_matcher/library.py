import json
from pathlib import Path

from job_matcher.ingest import parse_markdown_resume
from job_matcher.models import MarkdownResumeRequest, ResumeDocument


class ResumeLibraryError(RuntimeError):
    """Raised when the local canonical resume library is unavailable or malformed."""


def load_resume_library(root: Path) -> list[ResumeDocument]:
    if not root.is_dir():
        raise ResumeLibraryError(f"resume library directory does not exist: {root}")

    resumes: list[ResumeDocument] = []
    for metadata_path in sorted(root.glob("*/metadata.json")):
        directory = metadata_path.parent
        markdown_path = directory / "resume.md"
        if not markdown_path.is_file():
            raise ResumeLibraryError(f"resume Markdown is missing: {markdown_path}")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            request = MarkdownResumeRequest(
                id=metadata["id"],
                name=metadata["name"],
                role_family=metadata["role_family"],
                markdown=markdown_path.read_text(encoding="utf-8"),
            )
            resumes.append(parse_markdown_resume(request))
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            raise ResumeLibraryError(f"invalid resume library entry: {directory}") from error

    if not resumes:
        raise ResumeLibraryError(f"no resumes found in library: {root}")
    return resumes
