"""Spiegelt die Repo-`docs/*.md` als Starlight-MDX in die Marketing-Site.

Single Source of Truth bleibt das Repo-`docs/`-Verzeichnis (offline + auf GitHub
lesbar). Dieser Sync erzeugt deterministisch die Starlight-Pendants unter
`apps/marketing/src/content/docs/` mit passendem Frontmatter und umgeschriebenen
relativen Links.

Aufruf:
    python scripts/sync_docs_to_site.py            # --write (Default)
    python scripts/sync_docs_to_site.py --check     # exit 1 bei Drift

Phase 6 (Landing + Doku-Site), Stage 2.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOCS_DIR = _REPO_ROOT / "docs"
_SITE_DOCS_DIR = _REPO_ROOT / "apps" / "marketing" / "src" / "content" / "docs"

# Hinweis, der die generierten Dateien als nicht-handgepflegt markiert.
_GENERATED_BANNER = (
    "<!-- AUTOGENERIERT aus docs/ via scripts/sync_docs_to_site.py — nicht von Hand editieren. -->"
)


@dataclass(frozen=True)
class DocMapping:
    """Verbindet eine Repo-`docs/`-Quelle mit Ziel-Datei und Site-URL."""

    source: str  # Dateiname relativ zu docs/
    dest: str  # Pfad relativ zu apps/marketing/src/content/docs/
    url: str  # Site-URL für Link-Rewriting (mit führendem/trailing Slash)


# Single Source of Truth für Quelle → Ziel → URL.
DOC_MAPPINGS: tuple[DocMapping, ...] = (
    DocMapping("playbooks.md", "concepts/playbooks.md", "/concepts/playbooks/"),
    DocMapping("git-sources.md", "git-sources/index.md", "/git-sources/"),
    DocMapping("viewer.md", "viewer/index.md", "/viewer/"),
)

# Basename → Site-URL für das Umschreiben relativer Markdown-Links.
_LINK_URL_BY_SOURCE: dict[str, str] = {m.source: m.url for m in DOC_MAPPINGS}


def _yaml_quote(value: str) -> str:
    """Quotet einen String sicher als doppelt-gequoteten YAML-Scalar."""

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _extract_title_and_body(markdown: str) -> tuple[str, str]:
    """Trennt den ersten H1-Titel vom restlichen Markdown-Body."""

    lines = markdown.splitlines()
    title = ""
    body_start = 0
    for index, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = index + 1
            break
    body = "\n".join(lines[body_start:]).strip("\n")
    return title, body


def _extract_description(body: str) -> str:
    """Erster regulärer Paragraph (mehrzeilig zusammengefügt) als `description`."""

    collected: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            if collected:
                break
            continue
        if line.startswith(("#", ">", "-", "*", "|", "`", "<")):
            if collected:
                break
            continue
        collected.append(line)
    return " ".join(collected)


def _rewrite_links(body: str) -> str:
    """Schreibt relative `./<datei>.md`-Links auf Site-URLs um."""

    def _replace(match: re.Match[str]) -> str:
        source = match.group("source")
        anchor = match.group("anchor") or ""
        url = _LINK_URL_BY_SOURCE.get(source)
        if url is None:
            return match.group(0)
        return f"]({url}{anchor})"

    pattern = re.compile(r"\]\(\./(?P<source>[A-Za-z0-9_-]+\.md)(?P<anchor>#[^)]*)?\)")
    return pattern.sub(_replace, body)


def render_mdx(markdown: str) -> str:
    """Rendert eine Repo-`docs/`-Markdown-Quelle als Starlight-MDX-String."""

    title, body = _extract_title_and_body(markdown)
    description = _extract_description(body)
    body = _rewrite_links(body)

    frontmatter_lines = ["---", f"title: {_yaml_quote(title)}"]
    if description:
        frontmatter_lines.append(f"description: {_yaml_quote(description)}")
    frontmatter_lines.append("---")

    parts = ["\n".join(frontmatter_lines), _GENERATED_BANNER, body]
    return "\n\n".join(parts).rstrip("\n") + "\n"


def _iter_targets() -> list[tuple[Path, Path, str]]:
    """Liefert (Quellpfad, Zielpfad, gerendertes-MDX) je Mapping."""

    results: list[tuple[Path, Path, str]] = []
    for mapping in DOC_MAPPINGS:
        source_path = _DOCS_DIR / mapping.source
        dest_path = _SITE_DOCS_DIR / mapping.dest
        rendered = render_mdx(source_path.read_text(encoding="utf-8"))
        results.append((source_path, dest_path, rendered))
    return results


def run_sync(*, check: bool) -> int:
    """Führt den Sync aus. `check=True` schreibt nicht, sondern meldet Drift."""

    drift: list[str] = []
    for _source, dest_path, rendered in _iter_targets():
        if check:
            current = dest_path.read_text(encoding="utf-8") if dest_path.exists() else None
            if current != rendered:
                drift.append(str(dest_path.relative_to(_REPO_ROOT)))
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(rendered, encoding="utf-8")

    if check and drift:
        sys.stderr.write(
            "Doku-Site ist nicht synchron mit docs/. Betroffen:\n"
            + "\n".join(f"  - {path}" for path in drift)
            + "\nLauf `python scripts/sync_docs_to_site.py` zum Beheben.\n"
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Schreibt nicht; exit 1 wenn die Site von docs/ abweicht.",
    )
    args = parser.parse_args(argv)
    return run_sync(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
