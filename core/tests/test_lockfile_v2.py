"""Lockfile-Tests rund um yank_status, signature-Slot und v1/v2-Backward-Compat-Migration.

Ursprünglich Phase-2-Datei (v2-Bump); seit Phase-3-Stage-1b-β deckt sie auch die
v2→v3-Migration ab (`schema_version: 2`, `target: str` Top-Level werden Loader-seitig
zu `targets: list[str]` migriert). Seit Phase P5 schreibt der Writer v4
(Git-Ids + optionaler `source_commit`); Alt-Lockfiles bleiben lesbar.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from speccify_core import (
    CURRENT_LOCKFILE_SCHEMA_VERSION,
    GeneratorPin,
    LockEntry,
    Lockfile,
    LockfileError,
    NoneSignature,
    SigstoreSignature,
)

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64


def _entry(
    spec_id: str,
    sha: str,
    *,
    yank_status: str = "none",
    yank_reason: str | None = None,
) -> LockEntry:
    return LockEntry(
        id=spec_id,
        version="0.1.0",
        sha256=sha,
        resolved_via="registry-fixtures",
        target="react",
        generator=GeneratorPin(),
        generated_files_sha256=(),
        yank_status=yank_status,
        yank_reason=yank_reason,
    )


def test_lockfile_default_schema_version_is_v4() -> None:
    lock = Lockfile(targets=("react",))
    assert lock.schema_version == 4
    assert CURRENT_LOCKFILE_SCHEMA_VERSION == 4


def test_lockfile_default_signature_is_none() -> None:
    lock = Lockfile(targets=("react",))
    assert isinstance(lock.signature, NoneSignature)
    assert lock.signature.kind == "none"


def test_lockfile_v3_round_trip_with_yank_and_signature(tmp_path: Path) -> None:
    lock = Lockfile(
        targets=("react",),
        entries=(
            _entry("@org/button", _HASH_A),
            _entry(
                "@org/contact-form",
                _HASH_B,
                yank_status="yanked",
                yank_reason="security issue",
            ),
        ),
    )
    out = tmp_path / "speccify.lock"
    lock.write(out)
    loaded = Lockfile.load(out)
    assert loaded == lock
    by_id = {e.id: e for e in loaded.entries}
    assert by_id["@org/contact-form"].yank_status == "yanked"
    assert by_id["@org/contact-form"].yank_reason == "security issue"
    assert by_id["@org/button"].yank_status == "none"


def test_lockfile_with_yank_marks_entry_yanked() -> None:
    lock = Lockfile(targets=("react",), entries=(_entry("@org/button", _HASH_A),))
    updated = lock.with_yank("@org/button", status="yanked", reason="bad")
    entry = next(e for e in updated.entries if e.id == "@org/button")
    assert entry.yank_status == "yanked"
    assert entry.yank_reason == "bad"


def test_lockfile_with_yank_clears_reason_when_unyanked() -> None:
    lock = Lockfile(
        targets=("react",),
        entries=(_entry("@org/button", _HASH_A, yank_status="yanked", yank_reason="x"),),
    )
    updated = lock.with_yank("@org/button", status="none")
    entry = next(e for e in updated.entries if e.id == "@org/button")
    assert entry.yank_status == "none"
    assert entry.yank_reason is None


def test_lockfile_with_yank_rejects_invalid_status() -> None:
    lock = Lockfile(targets=("react",), entries=(_entry("@org/button", _HASH_A),))
    with pytest.raises(LockfileError):
        lock.with_yank("@org/button", status="bogus")


def test_lockfile_writes_signature_field(tmp_path: Path) -> None:
    lock = Lockfile(targets=("react",), entries=(_entry("@org/button", _HASH_A),))
    out = tmp_path / "speccify.lock"
    lock.write(out)
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["signature"] == {"kind": "none"}
    assert data["schema_version"] == 4


def test_lockfile_sigstore_signature_round_trip(tmp_path: Path) -> None:
    lock = Lockfile(
        targets=("react",),
        entries=(_entry("@org/button", _HASH_A),),
        signature=SigstoreSignature(certificate="PEM-DATA", rekor_log_index=42),
    )
    out = tmp_path / "speccify.lock"
    lock.write(out)
    loaded = Lockfile.load(out)
    assert loaded == lock
    assert isinstance(loaded.signature, SigstoreSignature)
    assert loaded.signature.rekor_log_index == 42


def test_lockfile_v1_loads_and_migrates_to_v4(tmp_path: Path) -> None:
    """Phase-1-Lockfiles (v1, ohne signature/yank_status/targets-list) bleiben lesbar."""

    v1 = tmp_path / "speccify.lock"
    v1.write_text(
        "schema_version: 1\n"
        "target: react\n"
        "specs:\n"
        "  - id: '@org/button'\n"
        "    version: '0.1.0'\n"
        f"    sha256: '{_HASH_A}'\n"
        "    resolved_via: registry-fixtures\n"
        "    target: react\n"
        "    generator: {kind: template, template_set: phase-1a-stub, template_version: 0.1.0}\n"
        "    generated_files_sha256: []\n",
        encoding="utf-8",
    )
    loaded = Lockfile.load(v1)
    assert loaded.schema_version == 4
    assert loaded.targets == ("react",)
    assert isinstance(loaded.signature, NoneSignature)
    assert loaded.entries[0].yank_status == "none"
    assert loaded.entries[0].yank_reason is None

    # Beim Re-Write wird das Lockfile auf v4 aktualisiert (Top-Level `targets`).
    out = tmp_path / "speccify.lock.new"
    loaded.write(out)
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 4
    assert data["targets"] == ["react"]
    assert "target" not in data
    assert data["signature"] == {"kind": "none"}
    assert data["specs"][0]["yank_status"] == "none"


def test_lockfile_v3_rejects_invalid_yank_status(tmp_path: Path) -> None:
    bad = tmp_path / "speccify.lock"
    bad.write_text(
        "schema_version: 3\n"
        "targets: ['react']\n"
        "signature: {kind: none}\n"
        "specs:\n"
        "  - id: '@org/button'\n"
        "    version: '0.1.0'\n"
        f"    sha256: '{_HASH_A}'\n"
        "    resolved_via: registry-fixtures\n"
        "    target: react\n"
        "    yank_status: 'bogus'\n"
        "    generator: {kind: template, template_set: phase-1a-stub, template_version: 0.1.0}\n"
        "    generated_files_sha256: []\n",
        encoding="utf-8",
    )
    with pytest.raises(LockfileError):
        Lockfile.load(bad)
