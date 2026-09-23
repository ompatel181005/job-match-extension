import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from job_matcher.ingest import parse_markdown_resume
from job_matcher.models import MarkdownResumeRequest, ResumeImportResult, ResumeSummary

SCHEMA_VERSION = 1


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    with closing(_connect(database_path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role_family TEXT,
                current_digest TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resume_versions (
                resume_id TEXT NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
                digest TEXT NOT NULL,
                markdown TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                PRIMARY KEY (resume_id, digest)
            );
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, datetime.now(UTC).isoformat()),
        )


def import_resume(database_path: Path, request: MarkdownResumeRequest) -> ResumeImportResult:
    document = parse_markdown_resume(request)
    digest = hashlib.sha256(request.markdown.encode("utf-8")).hexdigest()
    imported_at = datetime.now(UTC).isoformat()
    evidence_json = json.dumps(
        [item.model_dump(mode="json") for item in document.evidence],
        sort_keys=True,
        separators=(",", ":"),
    )

    initialize_database(database_path)
    with closing(_connect(database_path)) as connection, connection:
        existing_version = connection.execute(
            "SELECT 1 FROM resume_versions WHERE resume_id = ? AND digest = ?",
            (request.id, digest),
        ).fetchone()
        existing_resume = connection.execute(
            "SELECT 1 FROM resumes WHERE id = ?",
            (request.id,),
        ).fetchone()

        if existing_resume is None:
            connection.execute(
                """
                INSERT INTO resumes(
                    id, name, role_family, current_digest, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.id,
                    request.name,
                    request.role_family,
                    digest,
                    imported_at,
                    imported_at,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE resumes
                SET name = ?, role_family = ?, current_digest = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    request.name,
                    request.role_family,
                    digest,
                    imported_at,
                    request.id,
                ),
            )

        changed = existing_version is None
        if changed:
            connection.execute(
                """
                INSERT INTO resume_versions(
                    resume_id, digest, markdown, evidence_json, imported_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (request.id, digest, request.markdown, evidence_json, imported_at),
            )

        version = connection.execute(
            "SELECT COUNT(*) FROM resume_versions WHERE resume_id = ?",
            (request.id,),
        ).fetchone()[0]

    return ResumeImportResult(
        id=request.id,
        name=request.name,
        role_family=request.role_family,
        digest=digest,
        version=version,
        evidence_count=len(document.evidence),
        changed=changed,
    )


def list_resumes(database_path: Path) -> list[ResumeSummary]:
    initialize_database(database_path)
    with closing(_connect(database_path)) as connection:
        rows = connection.execute(
            """
            SELECT
                resumes.id,
                resumes.name,
                resumes.role_family,
                resumes.current_digest,
                resumes.updated_at,
                COUNT(resume_versions.digest) AS version_count
            FROM resumes
            JOIN resume_versions ON resume_versions.resume_id = resumes.id
            GROUP BY resumes.id
            ORDER BY resumes.name COLLATE NOCASE, resumes.id
            """
        ).fetchall()
    return [
        ResumeSummary(
            id=row["id"],
            name=row["name"],
            role_family=row["role_family"],
            current_digest=row["current_digest"],
            version_count=row["version_count"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
