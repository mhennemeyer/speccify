"""Tests für `speccify_core.conformance` (Phase 3 Stage 4 — static-validate-Backend).

Diese Tests bauen Lockfile-Instanzen in-memory und nutzen den Repo-Replay-Cache
(`tests/fixtures/llm-cache`) für deterministische Re-Renders. Sie sind bewusst
unabhängig vom CLI, damit das Conformance-Modul auch ohne `typer`/IO-Stack
getestet wird.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from speccify_core import (
    GeneratedFile,
    LlmGeneratorPin,
    LockEntry,
    Lockfile,
    ReplayCache,
    ReplayCacheClient,
    StaticValidateBackend,
    render_for_target,
    run_conformance,
)
from speccify_core.codegen import react_llm
from speccify_core.registry import LocalRegistry, Version

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"


def _client() -> ReplayCacheClient:
    return ReplayCacheClient(cache=ReplayCache(CACHE_DIR), offline=True)


def _render_button() -> tuple[dict[str, bytes], object]:
    registry = LocalRegistry(REGISTRY_FIXTURES)
    spec = registry.fetch("@org/button", Version.parse("0.1.0"))
    rendered = render_for_target(spec, "react", llm_client=_client())
    return rendered.files, rendered.cache_key


def _button_entry(files: dict[str, bytes], cache_key: object) -> LockEntry:
    gen_files = tuple(
        GeneratedFile(path=p, sha256=f"sha256:{hashlib.sha256(b).hexdigest()}")
        for p, b in files.items()
    )
    return LockEntry(
        id="@org/button",
        version="0.1.0",
        sha256="sha256:" + "0" * 64,  # nicht relevant — conformance prüft Re-Render-Hashes
        resolved_via="registry-fixtures",
        target="react",
        generator=LlmGeneratorPin(
            provider=react_llm.PROVIDER,
            model=react_llm.MODEL,
            prompt_version=react_llm.PROMPT_VERSION,
            cache_key=f"sha256:{cache_key.digest()}",  # type: ignore[attr-defined]
            seed=react_llm.DEFAULT_SEED,
        ),
        generated_files_sha256=gen_files,
    )


def test_conformance_happy_path_static_validate() -> None:
    files, key = _render_button()
    lock = Lockfile(targets=("react",), entries=(_button_entry(files, key),))
    report = run_conformance(
        lockfile=lock,
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert report.ok, [r.messages for r in report.failures()]
    assert report.backend == "static-validate"
    assert len(report.results) == 1
    assert report.results[0].status == "ok"
    assert report.results[0].target == "react"
    assert report.results[0].spec_id == "@org/button"


def test_conformance_detects_hash_drift() -> None:
    files, key = _render_button()
    entry = _button_entry(files, key)
    # Patche genau einen `generated_files_sha256`-Eintrag → Drift
    drifted = LockEntry(
        id=entry.id,
        version=entry.version,
        sha256=entry.sha256,
        resolved_via=entry.resolved_via,
        target=entry.target,
        generator=entry.generator,
        generated_files_sha256=(
            GeneratedFile(path=entry.generated_files_sha256[0].path, sha256="sha256:" + "f" * 64),
        ),
    )
    lock = Lockfile(targets=("react",), entries=(drifted,))
    report = run_conformance(
        lockfile=lock,
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert not report.ok
    assert len(report.failures()) == 1
    failure = report.failures()[0]
    assert failure.status == "hash_drift"
    assert any("Hash-Drift" in msg for msg in failure.messages)


def test_conformance_no_outputs_when_lockfile_entry_empty() -> None:
    files, key = _render_button()
    entry = _button_entry(files, key)
    empty = LockEntry(
        id=entry.id,
        version=entry.version,
        sha256=entry.sha256,
        resolved_via=entry.resolved_via,
        target=entry.target,
        generator=entry.generator,
        generated_files_sha256=(),
    )
    lock = Lockfile(targets=("react",), entries=(empty,))
    report = run_conformance(
        lockfile=lock,
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert not report.ok
    assert report.failures()[0].status == "no_outputs"


def test_conformance_target_filter_skips_nonmatching_entries() -> None:
    files, key = _render_button()
    lock = Lockfile(targets=("react",), entries=(_button_entry(files, key),))
    # Filter auf swiftui → Lockfile-Eintrag (target=react) wird übersprungen.
    report = run_conformance(
        lockfile=lock,
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
        targets=("swiftui",),
    )
    assert report.ok
    assert report.results == ()


def test_conformance_render_failed_on_cache_miss(tmp_path: Path) -> None:
    files, key = _render_button()
    lock = Lockfile(targets=("react",), entries=(_button_entry(files, key),))
    empty_cache = ReplayCacheClient(cache=ReplayCache(tmp_path), offline=True)
    report = run_conformance(
        lockfile=lock,
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=empty_cache,
    )
    assert not report.ok
    assert report.failures()[0].status == "render_failed"


def test_conformance_backend_protocol_static_validate_name() -> None:
    backend = StaticValidateBackend()
    assert backend.name == "static-validate"


def test_conformance_report_by_target_groups_results() -> None:
    files, key = _render_button()
    lock = Lockfile(targets=("react",), entries=(_button_entry(files, key),))
    report = run_conformance(
        lockfile=lock,
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    grouped = report.by_target()
    assert set(grouped.keys()) == {"react"}
    assert len(grouped["react"]) == 1


def test_conformance_unknown_status_via_unknown_target() -> None:
    files, key = _render_button()
    entry = _button_entry(files, key)
    bad = LockEntry(
        id=entry.id,
        version=entry.version,
        sha256=entry.sha256,
        resolved_via=entry.resolved_via,
        target="definitely-unknown-target",
        generator=entry.generator,
        generated_files_sha256=entry.generated_files_sha256,
    )
    lock = Lockfile(targets=("react",), entries=(bad,))
    report = run_conformance(
        lockfile=lock,
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert not report.ok
    assert report.failures()[0].status == "render_failed"


def test_replay_cache_dir_exists() -> None:
    """Fail-Fast: Wenn der Replay-Cache fehlt, sind alle anderen Tests irreführend."""
    assert CACHE_DIR.is_dir(), f"Replay-Cache fehlt: {CACHE_DIR}"
