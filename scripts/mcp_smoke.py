"""MCP-Smoke-Skript für `speccify-mcp` (Phase 1c Step 5).

Startet den `speccify-mcp`-Server per `stdio` als Subprocess, fährt
einen MCP-Handshake mit dem offiziellen Python-Client und prüft die
in Phase 1c versprochenen Grund-Roundtrips:

1. `tools/list` enthält exakt die 7 Tools `lint/lock/publish/pull/
   render/resolve/verify`.
2. `tools/call render` für `@org/button@0.1.0` (offline) liefert
   TSX-Bytes (mind. ein `export`-Statement) und `generator_pin.kind
   == "llm"`.
3. `resources/read speccify://manifest` liefert die `speccify.yaml`
   des Projekts.

Das Skript ist **offline** — `SPECCIFY_CACHE_DIR` wird auf den
eingecheckten Replay-Cache gepinnt und `ANTHROPIC_API_KEY` / Bedrock-
Creds werden bewusst nicht gesetzt.

Aufruf (CI):

    uv run python scripts/mcp_smoke.py

Exit-Code 0 = grün, alles andere = Fehler (mit Diagnose auf stderr).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PROJECT = REPO_ROOT / "example-project"
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"

EXPECTED_TOOLS = {"lint", "lock", "publish", "pull", "render", "resolve", "verify"}


def _prepare_workspace(tmp: Path) -> Path:
    """Kopiert example-project + registry-fixtures nach `tmp`.

    Das Manifest verweist relativ auf `../registry-fixtures`, also
    müssen beide nebeneinander liegen.
    """
    shutil.copytree(REGISTRY_FIXTURES, tmp / "registry-fixtures")
    project = tmp / "example-project"
    shutil.copytree(EXAMPLE_PROJECT, project)
    out = project / "out"
    if out.exists():
        shutil.rmtree(out)
    return project


async def _run(project_root: Path) -> None:
    # `speccify-mcp` als Console-Script via `uv run` aufzurufen wäre
    # in CI brüchig (uv im Pfad?); wir nutzen den installierten
    # Entry-Point direkt aus dem aktuellen Python.
    env = os.environ.copy()
    env["SPECCIFY_CACHE_DIR"] = str(LLM_CACHE)
    # Falls in einer Dev-Umgebung gesetzt: hart entfernen, damit der
    # Smoke garantiert offline läuft.
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("AWS_ACCESS_KEY_ID", None)
    env.pop("AWS_SECRET_ACCESS_KEY", None)

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "speccify_mcp.cli", "--project", str(project_root)],
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1) tools/list
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert names == EXPECTED_TOOLS, (
                f"tools/list mismatch: got {sorted(names)}, expected {sorted(EXPECTED_TOOLS)}"
            )
            print(f"[ok] tools/list = {sorted(names)}", file=sys.stderr)

            # 2) tools/call render @org/button (offline)
            result = await session.call_tool(
                "render",
                {"spec_id": "@org/button", "target": "react"},
            )
            assert not result.isError, f"render returned isError: {result}"
            payload = result.structuredContent or {}
            files = payload.get("files") or {}
            assert files, f"render: empty files payload: {payload}"
            first_path, first_text = next(iter(files.items()))
            assert "export" in first_text, (
                f"render: expected `export` in {first_path}, got: {first_text[:120]}..."
            )
            pin = payload.get("generator_pin") or {}
            assert pin.get("kind") == "llm", f"render: expected generator_pin.kind=llm, got {pin}"
            print(
                f"[ok] tools/call render → {len(files)} file(s), "
                f"generator_pin.kind={pin.get('kind')}",
                file=sys.stderr,
            )

            # 3) resources/read speccify://manifest
            res = await session.read_resource("speccify://manifest")
            assert res.contents, "resources/read returned no contents"
            text = getattr(res.contents[0], "text", "") or ""
            assert "schema_version: 1" in text, (
                f"manifest resource missing schema_version: {text[:120]}..."
            )
            assert "target: react" in text, f"manifest resource missing target: {text[:120]}..."
            print("[ok] resources/read speccify://manifest", file=sys.stderr)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        project = _prepare_workspace(Path(tmp))
        try:
            asyncio.run(_run(project))
        except AssertionError as exc:
            print(f"[fail] {exc}", file=sys.stderr)
            return 1
        except Exception as exc:  # pragma: no cover - diagnostic
            print(f"[fail] unexpected: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    print("speccify-mcp stdio smoke: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
