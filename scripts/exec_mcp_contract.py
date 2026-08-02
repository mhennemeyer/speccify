#!/usr/bin/env python3
"""Kontrakt-Diff-Harness für den Exec-MCP (Plan rust-neustart-toolkit-mcps.md, R0.3).

Schickt eine identische Szenario-Batterie an die Python-Referenz (dotagent,
Commit 2949d1d) und den Rust-Kandidaten (crates/exec-mcp, ab R1) und difft
die normalisierten Antworten. Vertrag: docs/exec-mcp-contract.md.

Stand R5: Speccify ruft dotagent nirgends mehr auf — dieser Harness ist das
letzte Werkzeug, das die Referenz noch braucht, und läuft nur noch bei
Änderungen am Wire-Vertrag. Ohne laufende Referenz (`--reference`) macht er
einen Selbsttest gegen den Kandidaten.

Beide Server müssen im MULTI-Modus laufen (ohne --project); jede Seite
bekommt ihr eigenes frisches Fixture-Projekt, damit sich Pending-/Consume-
Schreibzugriffe nicht mischen. Datei-Effekte (pending/allowlist) werden
mitverglichen. stdlib-only — bewusst ohne Abhängigkeit zur Speccify-Engine.

    python3 scripts/exec_mcp_contract.py --reference http://127.0.0.1:8765 \
        [--candidate http://127.0.0.1:8865] [--verbose]

Exit 0 = Parität (bzw. Selbsttest ohne --candidate gelaufen), 1 = Diffs.
"""

from __future__ import annotations

import argparse
import difflib
import http.client
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PY = sys.executable or "python3"

ALLOWLIST = [
    {"pattern": "echo", "permanent": True},
    {"pattern": PY, "permanent": True},
    {"pattern": "no-such-binary-xyz", "permanent": True},
    {"pattern": "printf", "permanent": False},  # Einmal-Freigabe (consume-Test)
]

ACTIONS = [
    {
        "name": "Echo",
        "command": "echo action-ok",
        "source": "bo",
        "confirmed": True,
        "toolbar": False,
    },
    {
        "name": "Unbestaetigt",
        "command": "echo nope",
        "source": "agent",
        "confirmed": False,
        "toolbar": False,
    },
    {
        "name": "NichtErlaubt",
        "command": "git status",
        "source": "bo",
        "confirmed": True,
        "toolbar": False,
    },
]


# -- HTTP-Helfer -------------------------------------------------------------


def _post(base: str, path: str, payload: bytes, timeout: float = 60.0):
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, _decode(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, _decode(exc.read())


def _decode(raw: bytes):
    """Antwort-Body vergleichbar machen: JSON wenn möglich, sonst Text/None."""
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def rpc(base: str, method: str, params: dict | None = None, request_id: int | None = 1):
    return _post(
        base,
        "/",
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                **({"params": params} if params is not None else {}),
            }
        ).encode(),
    )


def call_tool(base: str, name: str, arguments: dict):
    return rpc(base, "tools/call", {"name": name, "arguments": arguments})


def stream(base: str, body: dict, timeout: float = 60.0) -> list[dict]:
    """POST /stream lesen, bis der Server schließt; liefert die SSE-Events."""
    parsed = urlparse(base)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)
    connection.request(
        "POST", "/stream", json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    response = connection.getresponse()
    events: list[dict] = []
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    connection.close()
    return events


# -- Normalisierung -----------------------------------------------------------

VOLATILE_KEYS = {"duration_ms": "<dur>", "requested_at": "<ts>"}


def normalize(value: Any, project: str, scratch: str) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in VOLATILE_KEYS:
                out[key] = VOLATILE_KEYS[key]
            elif key == "serverInfo" and isinstance(item, dict):
                info = dict(item)
                info["name"] = "<server>"
                info["version"] = "<version>"
                out[key] = normalize(info, project, scratch)
            else:
                out[key] = normalize(item, project, scratch)
        return out
    if isinstance(value, (list, tuple)):
        return [normalize(item, project, scratch) for item in value]
    if isinstance(value, str):
        # Projekt VOR Scratch ersetzen (das Projekt liegt im Scratch-Dir).
        text = value.replace(project, "<project>").replace(scratch, "<scratch>")
        # Tool-Result-Texte sind oft selbst JSON — dann strukturell
        # normalisieren (macht duration_ms & Co. auch dort unschädlich).
        if text.startswith("{") or text.startswith("["):
            try:
                return normalize(json.loads(text), project, scratch)
            except json.JSONDecodeError:
                pass
        return text
    return value


# -- Fixture-Projekt ----------------------------------------------------------


def make_project(base_dir: Path) -> Path:
    project = base_dir / "fixture-project"
    agent = project / ".agent"
    agent.mkdir(parents=True)
    (agent / "exec-allowlist.json").write_text(
        json.dumps(ALLOWLIST, indent=2, ensure_ascii=False) + "\n"
    )
    (agent / "actions.json").write_text(json.dumps(ACTIONS, indent=2, ensure_ascii=False) + "\n")
    (base_dir / "kein-projekt").mkdir()  # Ordner ohne .agent/ (Ablehnungs-Test)
    return project


def read_json_file(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


# -- Szenarien -----------------------------------------------------------------
# Reihenfolge ist Teil des Kontrakts des Harness (Datei-Effekte bauen
# aufeinander auf); beide Seiten durchlaufen exakt dieselbe Sequenz.


def scenarios(base: str, project: Path, scratch: Path) -> dict[str, Any]:
    p = str(project)
    agent = project / ".agent"
    results: dict[str, Any] = {}

    with urllib.request.urlopen(base, timeout=10) as response:
        results["get_banner"] = {"status": response.status}  # Banner-Text: frei

    results["initialize"] = rpc(base, "initialize")
    results["notification"] = _post(
        base, "/", json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode()
    )
    results["tools_list"] = rpc(base, "tools/list")
    results["parse_error"] = _post(base, "/", b"das ist kein json")
    results["unknown_method"] = rpc(base, "does/not-exist")

    results["run_command_ok"] = call_tool(
        base, "run_command", {"command": "echo hallo", "project": p}
    )
    results["run_command_missing_command"] = call_tool(base, "run_command", {"project": p})
    results["run_command_denied"] = call_tool(
        base, "run_command", {"command": "git status", "project": p}
    )
    results["pending_after_denied"] = read_json_file(agent / "exec-pending.json")
    results["run_command_not_found"] = call_tool(
        base, "run_command", {"command": "no-such-binary-xyz --nope", "project": p}
    )
    results["run_command_capped"] = call_tool(
        base, "run_command", {"command": f"{PY} -c \"print('x' * 25000)\"", "project": p}
    )

    results["run_action_ok"] = call_tool(base, "run_action", {"name": "Echo", "project": p})
    results["run_action_unknown"] = call_tool(base, "run_action", {"name": "Nada", "project": p})
    results["run_action_unconfirmed"] = call_tool(
        base, "run_action", {"name": "Unbestaetigt", "project": p}
    )
    results["run_action_not_allowlisted"] = call_tool(
        base, "run_action", {"name": "NichtErlaubt", "project": p}
    )
    results["list_actions"] = call_tool(base, "list_actions", {"project": p})

    results["multi_missing_project"] = call_tool(base, "run_command", {"command": "echo x"})
    results["multi_relative_project"] = call_tool(
        base, "run_command", {"command": "echo x", "project": "rel/pfad"}
    )
    results["multi_no_agent_dir"] = call_tool(
        base, "run_command", {"command": "echo x", "project": str(scratch / "kein-projekt")}
    )
    results["multi_project_not_string"] = call_tool(
        base, "run_command", {"command": "echo x", "project": 42}
    )

    results["stream_ok"] = stream(base, {"command": "echo s1", "project": p})
    results["stream_stderr_merge"] = stream(
        base,
        {
            "command": (
                f"{PY} -c \"import sys; print('out'); sys.stdout.flush(); "
                f"print('err', file=sys.stderr)\""
            ),
            "project": p,
        },
    )
    results["stream_denied"] = stream(base, {"command": "git push", "project": p})
    results["stream_missing_project"] = stream(base, {"command": "echo x"})
    results["stream_missing_command"] = stream(base, {"project": p})

    # Einmal-Freigabe: Lauf konsumiert den printf-Eintrag aus der Allowlist.
    results["oneshot_run"] = call_tool(
        base, "run_command", {"command": "printf one-shot-ok", "project": p}
    )
    results["allowlist_after_oneshot"] = read_json_file(agent / "exec-allowlist.json")

    return {name: normalize(value, p, str(scratch)) for name, value in results.items()}


# -- Vergleich ------------------------------------------------------------------


def run_side(base: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="exec-mcp-contract-") as tmp:
        scratch = Path(tmp).resolve()
        project = make_project(scratch)
        return scenarios(base, project, scratch)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference", required=True, help="Basis-URL der Python-Referenz (Multi-Modus)."
    )
    parser.add_argument("--candidate", help="Basis-URL des Rust-Kandidaten (Multi-Modus).")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    reference = run_side(args.reference)
    if args.candidate is None:
        print(json.dumps(reference, indent=2, ensure_ascii=False, sort_keys=True))
        print(
            f"\nSelbsttest: {len(reference)} Szenarien gegen "
            f"{args.reference} gelaufen (kein Kandidat angegeben)."
        )
        return 0

    candidate = run_side(args.candidate)
    failures = 0
    for name in reference:
        ref_text = json.dumps(reference[name], indent=2, ensure_ascii=False, sort_keys=True)
        cand_text = json.dumps(candidate.get(name), indent=2, ensure_ascii=False, sort_keys=True)
        if ref_text == cand_text:
            if args.verbose:
                print(f"OK   {name}")
            continue
        failures += 1
        print(f"DIFF {name}")
        diff = difflib.unified_diff(
            ref_text.splitlines(),
            cand_text.splitlines(),
            fromfile=f"referenz/{name}",
            tofile=f"kandidat/{name}",
            lineterm="",
        )
        for line in diff:
            print(f"  {line}")

    total = len(reference)
    if failures:
        print(f"\n{failures}/{total} Szenarien weichen ab — keine Parität.")
        return 1
    print(f"\nParität: alle {total} Szenarien identisch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
