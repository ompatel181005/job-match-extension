import json

from fastapi.testclient import TestClient

from job_matcher.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_rank_endpoint() -> None:
    response = client.post(
        "/v1/matches/rank",
        json={
            "requirements": [
                {"id": "python", "text": "Python", "keywords": ["Python"]},
            ],
            "resumes": [
                {
                    "id": "backend",
                    "name": "Backend",
                    "evidence": [
                        {"id": "b1", "section": "experience", "text": "Built with Python"},
                    ],
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["matches"][0]["score"] == 100


def test_extract_job_endpoint() -> None:
    response = client.post(
        "/v1/jobs/extract",
        json={
            "title": "Backend Engineer",
            "text": "Python and FastAPI experience required. Docker is a nice to have.",
        },
    )

    assert response.status_code == 200
    requirements = response.json()["requirements"]
    assert [item["keywords"] for item in requirements] == [["python"], ["fastapi"], ["docker"]]
    assert requirements[0]["priority"] == "required"
    assert requirements[2]["priority"] == "preferred"


def test_parse_markdown_endpoint() -> None:
    response = client.post(
        "/v1/resumes/parse-markdown",
        json={
            "id": "backend",
            "name": "Backend Base",
            "role_family": "backend",
            "markdown": "# Resume\n## Experience\n- Built Python APIs.\n## Skills\nPython, FastAPI",
        },
    )

    assert response.status_code == 200
    evidence = response.json()["evidence"]
    assert [item["section"] for item in evidence] == ["experience", "skills"]


def test_rank_job_uses_local_library(tmp_path, monkeypatch) -> None:
    directory = tmp_path / "backend"
    directory.mkdir()
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "id": "backend",
                "name": "Backend Base",
                "role_family": "backend",
                "updated_at": "2026-09-21T00:00:00Z",
            }
        )
    )
    (directory / "resume.md").write_text(
        "## Experience\n- Built Python services with FastAPI.\n## Skills\nPython, FastAPI"
    )
    monkeypatch.setenv("JOB_MATCHER_RESUME_DIR", str(tmp_path))

    response = client.post(
        "/v1/jobs/rank",
        json={"text": "Python and FastAPI experience required."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ranking"]["matches"][0]["resume_id"] == "backend"
    assert payload["ranking"]["matches"][0]["score"] == 100
