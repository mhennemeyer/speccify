#!/usr/bin/env python3
"""gitlab-deploy-key — see TOOL.md for the contract.

One JSON object on stdin, one on stdout. `plan` never touches the network;
`check` only reads; `apply` creates the key once and enables it elsewhere.
The token comes from GITLAB_TOKEN and is never echoed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

KEY_TYPES = {
    "ssh-ed25519",
    "ssh-rsa",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "sk-ssh-ed25519@openssh.com",
    "sk-ecdsa-sha2-nistp256@openssh.com",
}
MAINTAINER = 40


class Fail(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.message = message
        self.code = code


def fail(message: str, code: int = 1) -> None:
    json.dump({"ok": False, "error": message}, sys.stdout)
    sys.stdout.write("\n")
    sys.stderr.write(message + "\n")
    sys.exit(code)


def fingerprint_of(key: str) -> str:
    parts = key.strip().split()
    if len(parts) < 2 or parts[0] not in KEY_TYPES:
        raise Fail("key is not an OpenSSH public key line (expected `ssh-ed25519 AAAA…`)")
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except Exception:
        raise Fail("key is not an OpenSSH public key line (expected `ssh-ed25519 AAAA…`)") from None
    # The blob starts with the length-prefixed key type; it must match the prefix.
    if len(blob) < 4:
        raise Fail("key is not an OpenSSH public key line (expected `ssh-ed25519 AAAA…`)")
    length = int.from_bytes(blob[:4], "big")
    if blob[4 : 4 + length].decode("ascii", "replace") != parts[0]:
        raise Fail("key type in the blob does not match its prefix")
    digest = hashlib.sha256(blob).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def read_input() -> dict:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise Fail(f"stdin is not a JSON object: {exc}") from exc
    if not isinstance(data, dict):
        raise Fail("stdin is not a JSON object")
    host = str(data.get("host") or "").strip()
    host = host.removeprefix("https://").removeprefix("http://").rstrip("/")
    if not host:
        raise Fail("host is required")
    projects = data.get("projects")
    if (
        not isinstance(projects, list)
        or not projects
        or not all(isinstance(p, str) and "/" in p for p in projects)
    ):
        raise Fail("projects must name at least one project (group/name)")
    title = str(data.get("title") or "").strip()
    if not title:
        raise Fail("title is required")
    key = str(data.get("key") or "")
    mode = data.get("mode", "plan")
    if mode not in ("plan", "check", "apply"):
        raise Fail("mode must be plan, check or apply")
    can_push = bool(data.get("can_push", False))
    return {
        "host": host,
        "projects": [p.strip().strip("/") for p in projects],
        "title": title,
        "key": key.strip(),
        "can_push": can_push,
        "mode": mode,
        "fingerprint": fingerprint_of(key),
    }


class Api:
    def __init__(self, host: str, token: str):
        self.base = f"https://{host}/api/v4"
        self.token = token

    def call(self, method: str, path: str, body: dict | None = None):
        request = urllib.request.Request(self.base + path, method=method)
        request.add_header("PRIVATE-TOKEN", self.token)
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, payload, timeout=30) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                message = json.loads(raw)
                message = message.get("message", message) if isinstance(message, dict) else message
            except Exception:
                message = raw.decode("utf-8", "replace")[:200]
            return exc.code, {"message": message}
        except urllib.error.URLError as exc:
            raise Fail(f"cannot reach {self.base}: {exc.reason}") from exc


def access_level(project: dict) -> int:
    permissions = project.get("permissions") or {}
    levels = [
        (permissions.get("project_access") or {}).get("access_level", 0),
        (permissions.get("group_access") or {}).get("access_level", 0),
    ]
    return max(int(level or 0) for level in levels)


def blob_of(key_line: str) -> str:
    parts = key_line.split()
    return parts[1] if len(parts) >= 2 else ""


def inspect_project(
    api: Api, path: str, fingerprint: str, can_push: bool, key_line: str = ""
) -> dict:
    encoded = urllib.parse.quote(path, safe="")
    status, project = api.call("GET", f"/projects/{encoded}")
    if status != 200:
        return {
            "path": path,
            "state": "error",
            "detail": f"HTTP {status}: {project.get('message')}",
        }
    entry = {"path": path, "id": project["id"], "access_level": access_level(project)}
    status, keys = api.call("GET", f"/projects/{project['id']}/deploy_keys?per_page=100")
    if status != 200:
        entry.update(state="error", detail=f"deploy_keys HTTP {status}: {keys.get('message')}")
        return entry
    # GitLab reports `fingerprint_sha256` without the `SHA256:` prefix (19.x);
    # compare the bare digest, and fall back to the key blob itself.
    wanted = fingerprint.removeprefix("SHA256:").rstrip("=")
    match = next(
        (
            k
            for k in keys
            if (k.get("fingerprint_sha256") or "").removeprefix("SHA256:").rstrip("=") == wanted
            or blob_of(k.get("key") or "") == blob_of(key_line)
        ),
        None,
    )
    if match is None:
        entry["state"] = "missing"
    else:
        entry["key_id"] = match["id"]
        entry["state"] = "present" if bool(match.get("can_push")) == can_push else "mismatch"
        if entry["state"] == "mismatch":
            entry["detail"] = (
                f"present as '{match.get('title')}' with can_push={match.get('can_push')}"
            )
    return entry


def main() -> None:
    spec = read_input()
    result = {
        "ok": True,
        "mode": spec["mode"],
        "fingerprint": spec["fingerprint"],
        "title": spec["title"],
        "can_push": spec["can_push"],
        "projects": [],
    }
    if spec["mode"] == "plan":
        result["projects"] = [{"path": p, "state": "planned"} for p in spec["projects"]]
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
        return

    token = os.environ.get("GITLAB_TOKEN", "")
    if not token:
        raise Fail("GITLAB_TOKEN is not set (scope api, Maintainer or above on every project)", 2)
    api = Api(spec["host"], token)

    status, user = api.call("GET", "/user")
    if status != 200:
        raise Fail(f"token rejected by {spec['host']}: HTTP {status} {user.get('message')}", 2)
    result["user"] = user.get("username", "")
    status, own = api.call("GET", "/personal_access_tokens/self")
    if status == 200 and isinstance(own, dict):
        result["scopes"] = list(own.get("scopes") or [])

    projects = [
        inspect_project(api, p, spec["fingerprint"], spec["can_push"], spec["key"])
        for p in spec["projects"]
    ]

    if spec["mode"] == "apply":
        key_id = next(
            (p.get("key_id") for p in projects if p.get("state") in ("present", "mismatch")), None
        )
        for entry in projects:
            if entry["state"] != "missing":
                continue
            if entry.get("access_level", 0) < MAINTAINER:
                entry.update(state="error", detail="needs Maintainer or above to add a deploy key")
                continue
            if key_id is None:
                status, created = api.call(
                    "POST",
                    f"/projects/{entry['id']}/deploy_keys",
                    {"title": spec["title"], "key": spec["key"], "can_push": spec["can_push"]},
                )
                if status not in (200, 201):
                    entry.update(
                        state="error", detail=f"create HTTP {status}: {created.get('message')}"
                    )
                    continue
                key_id = created["id"]
                entry.update(state="created", key_id=key_id)
            else:
                status, enabled = api.call(
                    "POST", f"/projects/{entry['id']}/deploy_keys/{key_id}/enable"
                )
                if status not in (200, 201):
                    entry.update(
                        state="error", detail=f"enable HTTP {status}: {enabled.get('message')}"
                    )
                    continue
                entry.update(state="enabled", key_id=key_id)
        # Prove it: read again, keep what apply did as the state, verify presence.
        for entry in projects:
            if entry.get("state") in ("created", "enabled"):
                again = inspect_project(
                    api, entry["path"], spec["fingerprint"], spec["can_push"], spec["key"]
                )
                if again.get("state") != "present":
                    seen = f"{again.get('state')}: {again.get('detail', '')}".strip(": ")
                    entry.update(state="error", detail=f"after apply the key is {seen}")

    result["projects"] = projects
    good = {"present", "created", "enabled"}
    result["ok"] = (
        all(p.get("state") in good for p in projects)
        if spec["mode"] == "apply"
        else all(p.get("state") in ("present", "missing", "mismatch") for p in projects)
    )
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    if not result["ok"]:
        problems = [
            f"{p['path']}: {p.get('state')} {p.get('detail', '')}".strip()
            for p in projects
            if p.get("state") not in good
        ]
        sys.stderr.write("; ".join(problems) + "\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Fail as exc:
        fail(exc.message, exc.code)
