import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from job_matcher import __version__
from job_matcher.extraction import extract_requirements
from job_matcher.ingest import parse_markdown_resume
from job_matcher.library import ResumeLibraryError, load_resume_library
from job_matcher.models import (
    JobExtractRequest,
    JobExtractResponse,
    JobRankResponse,
    MarkdownResumeRequest,
    RankRequest,
    RankResponse,
    ResumeDocument,
)
from job_matcher.scoring import rank_resumes

app = FastAPI(
    title="Job Matcher API",
    version=__version__,
    description="Explainable requirement coverage and resume-base ranking.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/v1/matches/rank", response_model=RankResponse)
def rank(request: RankRequest) -> RankResponse:
    return rank_resumes(request)


@app.post("/v1/jobs/extract", response_model=JobExtractResponse)
def extract_job(request: JobExtractRequest) -> JobExtractResponse:
    return extract_requirements(request)


@app.post("/v1/jobs/rank", response_model=JobRankResponse)
def rank_job(request: JobExtractRequest) -> JobRankResponse:
    extraction = extract_requirements(request)
    if not extraction.requirements:
        raise HTTPException(status_code=422, detail=extraction.warnings[0])
    library_root = Path(os.environ.get("JOB_MATCHER_RESUME_DIR", "data/private/resumes"))
    try:
        resumes = load_resume_library(library_root)
    except ResumeLibraryError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    ranking = rank_resumes(RankRequest(requirements=extraction.requirements, resumes=resumes))
    return JobRankResponse(extraction=extraction, ranking=ranking)


@app.post("/v1/resumes/parse-markdown", response_model=ResumeDocument)
def parse_resume(request: MarkdownResumeRequest) -> ResumeDocument:
    return parse_markdown_resume(request)
