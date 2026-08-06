"""Discovery through static index repositories.

Es gibt kein zentrales Registry mehr — Discovery läuft wie bei Homebrew-Taps
oder Scoop-Buckets über **Git-Repos mit einer Datei pro Spec-Repo**:

    <index-repo>/entries/<beliebiger-name>.yaml

Eine Datei pro Eintrag (Entscheidung D21) ist Absicht: ein PR fasst genau eine
Datei an, es gibt keine Merge-Konflikte in einer wachsenden Sammelliste, und
CI kann jeden Eintrag einzeln validieren.

Der Index sagt **nur, wo eine Spec liegt** — nie, welche Versionen es gibt.
Versionen sind Git-Tags und damit immer aktuell; ein Index kann gar nicht
veralten.

Quellen sind lokale Verzeichnisse oder Git-Refs (`git+<url>`); Git-Indizes
liegen im selben Bare-Clone-Cache wie Spec-Quellen und sind danach offline
lesbar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from speccify_core.git_registry import (
    GitRegistryError,
    GitRepoCache,
    is_git_ref,
    parse_git_ref,
)

INDEX_ENTRY_DIR = "entries"
INDEX_ENTRY_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "index-entry.schema.json"
)


class IndexError_(Exception):
    """Index-Quelle war nicht lesbar oder ein Eintrag ist ungültig."""


# Sprechender Alias — `IndexError` ist ein Builtin, deshalb der Unterstrich oben.
SpecIndexError = IndexError_


@dataclass(frozen=True)
class IndexEntry:
    """Ein Eintrag: Zeiger auf ein Spec-Repo plus Beschreibung für die Suche."""

    source: str
    title: str
    summary: str
    kind: str = ""
    keywords: tuple[str, ...] = ()
    homepage: str | None = None
    license: str | None = None
    # Woher der Eintrag kam (Index-Quelle) — für `speccify search`-Output.
    origin: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "kind": self.kind,
            "keywords": list(self.keywords),
            "homepage": self.homepage,
            "license": self.license,
            "origin": self.origin,
        }


@dataclass
class _Validator:
    schema_path: Path
    _validator: Draft202012Validator | None = field(default=None, init=False, repr=False)

    def issues(self, data: object) -> list[str]:
        if self._validator is None:
            schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
            self._validator = Draft202012Validator(schema)
        errors = sorted(self._validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        return [
            f"{'/'.join(str(p) for p in error.absolute_path) or '$'}: {error.message}"
            for error in errors
        ]


_ENTRY_VALIDATOR = _Validator(INDEX_ENTRY_SCHEMA_PATH)


def parse_index_entry(raw: bytes, *, origin: str, name: str) -> IndexEntry:
    """Parst und validiert genau einen Eintrag."""
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise SpecIndexError(f"{origin}/{name}: kaputtes YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecIndexError(f"{origin}/{name}: Eintrag muss ein Mapping sein.")
    issues = _ENTRY_VALIDATOR.issues(data)
    if issues:
        raise SpecIndexError(f"{origin}/{name}: {'; '.join(issues)}")
    return IndexEntry(
        source=str(data["source"]),
        title=str(data["title"]),
        summary=str(data["summary"]),
        kind=str(data.get("kind", "")),
        keywords=tuple(str(k) for k in data.get("keywords", ())),
        homepage=data.get("homepage"),
        license=data.get("license"),
        origin=origin,
    )


def load_index(
    source: str | Path,
    *,
    cache: GitRepoCache | None = None,
) -> list[IndexEntry]:
    """Lädt alle Einträge einer Index-Quelle (lokales Verzeichnis oder Git-Ref)."""
    if isinstance(source, str) and is_git_ref(source):
        return _load_git_index(source, cache=cache)
    return _load_local_index(Path(source))


def _load_local_index(root: Path) -> list[IndexEntry]:
    entries_dir = root / INDEX_ENTRY_DIR if (root / INDEX_ENTRY_DIR).is_dir() else root
    if not entries_dir.is_dir():
        raise SpecIndexError(f"Index-Quelle {root} existiert nicht.")
    entries = [
        parse_index_entry(path.read_bytes(), origin=str(root), name=path.name)
        for path in sorted(entries_dir.glob("*.yaml"))
    ]
    return _deduplicate(entries)


def _load_git_index(source: str, *, cache: GitRepoCache | None) -> list[IndexEntry]:
    repo_cache = cache or GitRepoCache()
    ref = parse_git_ref(source)
    prefix = f"{ref.path}/" if ref.path else ""
    try:
        repo = repo_cache.ensure(ref.url, refspec="HEAD", label=source)
        listing = repo_cache.run(
            ["ls-tree", "-r", "--name-only", "FETCH_HEAD", f"{prefix}{INDEX_ENTRY_DIR}/"],
            cwd=repo,
        )
    except GitRegistryError as exc:
        raise SpecIndexError(f"Index-Quelle {source} nicht lesbar: {exc}") from exc

    entries: list[IndexEntry] = []
    for path in sorted(line.strip() for line in listing.splitlines() if line.strip()):
        if not path.endswith(".yaml"):
            continue
        blob = repo_cache.run_bytes(["cat-file", "blob", f"FETCH_HEAD:{path}"], cwd=repo)
        entries.append(parse_index_entry(blob, origin=source, name=Path(path).name))
    return _deduplicate(entries)


def _deduplicate(entries: list[IndexEntry]) -> list[IndexEntry]:
    """Eine Quelle darf dieselbe Spec-Quelle nicht zweimal führen."""
    seen: dict[str, IndexEntry] = {}
    for entry in entries:
        if entry.source in seen:
            raise SpecIndexError(
                f"{entry.origin}: '{entry.source}' ist doppelt im Index "
                f"(einmal als '{seen[entry.source].title}', einmal als '{entry.title}')."
            )
        seen[entry.source] = entry
    return list(seen.values())


def load_indexes(
    sources: list[str | Path],
    *,
    cache: GitRepoCache | None = None,
) -> list[IndexEntry]:
    """Mehrere Quellen zusammenführen; die erste Nennung einer Spec-Quelle gewinnt."""
    merged: dict[str, IndexEntry] = {}
    for source in sources:
        for entry in load_index(source, cache=cache):
            merged.setdefault(entry.source, entry)
    return list(merged.values())


def score_entry(entry: IndexEntry, query: str) -> int:
    """Trefferstärke (0 = kein Treffer). Reihenfolge: Id > Titel > Keyword > Summary."""
    needle = query.strip().lower()
    if not needle:
        return 1
    if needle == entry.source.lower():
        return 100
    score = 0
    if needle in entry.source.lower():
        score = max(score, 40)
    if needle in entry.title.lower():
        score = max(score, 30)
    if any(needle in keyword.lower() for keyword in entry.keywords):
        score = max(score, 20)
    if needle in entry.summary.lower():
        score = max(score, 10)
    return score


def search_index(entries: list[IndexEntry], query: str) -> list[IndexEntry]:
    """Sucht case-insensitiv über Id/Titel/Keywords/Summary; leere Query listet alles."""
    scored = [(score_entry(entry, query), entry) for entry in entries]
    hits = [(score, entry) for score, entry in scored if score > 0]
    hits.sort(key=lambda item: (-item[0], item[1].source))
    return [entry for _, entry in hits]


__all__ = [
    "INDEX_ENTRY_DIR",
    "INDEX_ENTRY_SCHEMA_PATH",
    "IndexEntry",
    "SpecIndexError",
    "load_index",
    "load_indexes",
    "parse_index_entry",
    "score_entry",
    "search_index",
]
