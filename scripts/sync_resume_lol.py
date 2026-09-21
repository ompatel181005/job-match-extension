#!/usr/bin/env python3
"""Sync canonical resume.lol bases into ignored local storage."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

MCP_URL = "https://www.resume.lol/api/mcp"
CANONICAL_RESUMES = {
    "Om Patel — SWE": "swe",
    "Om Patel — Data Engineering": "data-engineering",
    "Om Patel — AI ML": "ai-ml",
    "Om Patel — Applied AI": "applied-ai",
    "Om Patel — Technical Product": "technical-product",
    "Om Patel — Forward Deployed": "forward-deployed",
    "Om Patel — Quant Dev": "quant-dev",
    "Om Patel — Quant Trader": "quant-trader",
    "Om Patel — Data Analytics": "data-analytics",
}


def _decode_sse(payload: str) -> dict[str, Any]:
    for line in payload.splitlines():
        if line.startswith("data: "):
            message = json.loads(line.removeprefix("data: "))
            if "error" in message:
                raise RuntimeError(message["error"])
            return message["result"]
    raise RuntimeError("resume.lol returned no MCP data event")


def _mcp_call(token: str, request_id: int, tool: str, arguments: dict[str, Any]) -> Any:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
    ).encode()
    request = urllib.request.Request(
        MCP_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = _decode_sse(response.read().decode())
    content = result.get("content", [])
    if not content or content[0].get("type") != "text":
        raise RuntimeError(f"{tool} returned no text content")
    return json.loads(content[0]["text"])


def _safe_directory_name(role_family: str) -> str:
    if not re.fullmatch(r"[a-z0-9-]+", role_family):
        raise ValueError(f"unsafe role-family directory: {role_family}")
    return role_family


def _write_resume(root: Path, role_family: str, resume: dict[str, Any]) -> None:
    destination = root / _safe_directory_name(role_family)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "resume.md").write_text(resume["markdown"], encoding="utf-8")
    (destination / "resume.css").write_text(resume.get("css", ""), encoding="utf-8")
    (destination / "settings.css").write_text(resume.get("meta_css", ""), encoding="utf-8")
    metadata = {
        "id": resume["id"],
        "name": resume["name"],
        "role_family": role_family,
        "updated_at": resume["updated_at"],
    }
    (destination / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def sync(output: Path, token: str) -> list[dict[str, str]]:
    listed = _mcp_call(token, 1, "list_resumes", {})
    by_name = {item["name"]: item for item in listed}
    missing = sorted(set(CANONICAL_RESUMES) - set(by_name))
    if missing:
        raise RuntimeError(f"canonical resumes not found: {', '.join(missing)}")

    synced: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                _mcp_call, token, index, "get_resume", {"resume_id": by_name[name]["id"]}
            ): (
                name,
                role_family,
            )
            for index, (name, role_family) in enumerate(CANONICAL_RESUMES.items(), start=2)
        }
        for future in as_completed(futures):
            name, role_family = futures[future]
            resume = future.result()
            _write_resume(output, role_family, resume)
            synced.append(
                {
                    "name": name,
                    "role_family": role_family,
                    "updated_at": resume["updated_at"],
                }
            )

    synced.sort(key=lambda item: item["role_family"])
    (output / "index.json").write_text(json.dumps(synced, indent=2) + "\n", encoding="utf-8")
    return synced


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/private/resumes"))
    args = parser.parse_args()
    token = os.environ.get("RESUME_LOL_MCP_TOKEN", "").strip()
    if not token:
        raise SystemExit("RESUME_LOL_MCP_TOKEN is not set")
    synced = sync(args.output, token)
    print(f"Synced {len(synced)} canonical resumes to {args.output}")
    for item in synced:
        print(f"- {item['role_family']}: {item['name']} ({item['updated_at']})")


if __name__ == "__main__":
    main()
