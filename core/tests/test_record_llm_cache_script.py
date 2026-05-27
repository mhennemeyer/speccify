"""Phase-5b-Stage-1-Test: validiert das target-aware `scripts/record_llm_cache.py`.

Greift bewusst **nicht** aufs Netz zu — geprüft werden nur das
Argparse-/Target-Resolver-Verhalten sowie der dynamische Modul-Loader, damit
das Phase-1b-Backcompat (Default `--target react`) und die neuen Targets
(`angular`/`swiftui`/`all`/Komma-Liste) reproduzierbar in CI laufen.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "record_llm_cache.py"


def _load_script_module():  # type: ignore[no-untyped-def]
    """Lädt `scripts/record_llm_cache.py` als ad-hoc Modul (kein Paket)."""
    spec = importlib.util.spec_from_file_location("_record_llm_cache_under_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


SCRIPT = _load_script_module()


def test_resolve_targets_default_is_react_backcompat() -> None:
    # Phase-1b-Verhalten muss erhalten bleiben: Default-CLI = nur React.
    assert SCRIPT._resolve_targets("react") == ["react"]


def test_resolve_targets_all_expands_to_three_targets() -> None:
    assert SCRIPT._resolve_targets("all") == ["react", "angular", "swiftui"]


def test_resolve_targets_csv_preserves_order() -> None:
    assert SCRIPT._resolve_targets("angular,swiftui") == ["angular", "swiftui"]
    assert SCRIPT._resolve_targets("swiftui, angular") == ["swiftui", "angular"]


def test_resolve_targets_rejects_unknown_target() -> None:
    with pytest.raises(SystemExit) as exc:
        SCRIPT._resolve_targets("react,vue")
    assert "vue" in str(exc.value)


@pytest.mark.parametrize(
    ("target", "expected_module_suffix", "normalize_attr", "validate_attr"),
    [
        ("react", "react_llm", "normalize_tsx", "validate_tsx"),
        ("angular", "angular_llm", "normalize_ts", "validate_ts"),
        ("swiftui", "swiftui_llm", "normalize_swift", "validate_swift"),
    ],
)
def test_load_target_module_wires_correct_codegen(
    target: str,
    expected_module_suffix: str,
    normalize_attr: str,
    validate_attr: str,
) -> None:
    mod, normalize_fn, validate_fn = SCRIPT._load_target_module(target)
    assert mod.__name__.endswith(expected_module_suffix)
    assert hasattr(mod, "MODEL")
    assert hasattr(mod, "build_prompt")
    assert hasattr(mod, "make_cache_key")
    assert normalize_fn is getattr(mod, normalize_attr)
    assert validate_fn is getattr(mod, validate_attr)


def test_load_target_module_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        SCRIPT._load_target_module("vue")
