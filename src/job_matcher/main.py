import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
    ResumeImportResult,
    ResumeSummary,
)
from job_matcher.scoring import rank_resumes
from job_matcher.storage import import_resume, list_resumes

app = FastAPI(
    title="Job Matcher API",
    version=__version__,
    description="Explainable requirement coverage and resume-base ranking.",
)
extension_origin = os.environ.get(
    "JOB_MATCHER_EXTENSION_ORIGIN",
    "chrome-extension://jefhfkhhkceplieedoffmceeglbbdfgk",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[extension_origin],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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


@app.post("/v1/resumes/import", response_model=ResumeImportResult)
def import_resume_endpoint(request: MarkdownResumeRequest) -> ResumeImportResult:
    database_path = Path(os.environ.get("JOB_MATCHER_DATABASE_PATH", "data/job_matcher.db"))
    return import_resume(database_path, request)


@app.get("/v1/resumes", response_model=list[ResumeSummary])
def list_resumes_endpoint() -> list[ResumeSummary]:
    database_path = Path(os.environ.get("JOB_MATCHER_DATABASE_PATH", "data/job_matcher.db"))
    return list_resumes(database_path)
