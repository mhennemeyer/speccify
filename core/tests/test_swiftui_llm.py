"""Tests für `speccify_core.codegen.swiftui_llm` + Dispatcher (Phase 3 Stage 2).

Analog zu `test_react_llm.py` (Phase 1b): inline Replay-Cache via `tmp_path`,
keine eingecheckten Golden Renders oder Replay-Fixtures. Golden Renders mit
echten LLM-Outputs sind Stage 4 (Conformance-Runner) vorbehalten.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    SUPPORTED_TARGETS,
    CacheMissError,
    CodegenError,
    ReplayCache,
    ReplayCacheClient,
    TargetRender,
    render_for_target,
)
from speccify_core.codegen import swiftui_llm
from speccify_core.registry import LocalRegistry, Version

REGISTRY_FIXTURES = Path(__file__).resolve().parents[2] / "registry-fixtures"


def _load_button() -> object:
    registry = LocalRegistry(REGISTRY_FIXTURES)
    return registry.fetch("@org/button", Version.parse("0.1.0"))


_VALID_BUTTON_SWIFT = """\
import SwiftUI

struct Button: View {
    var label: String
    var variant: String = "primary"
    var size: String = "md"
    var disabled: Bool = false
    var loading: Bool = false
    var iconLeading: String? = nil
    var onPressed: (() -> Void)? = nil
    var onLongPressed: (() -> Void)? = nil

    var body: some View {
        VStack {
            Text(label)
            Text("variant: \\(variant)")
        }
    }
}
"""


# --- normalize_swift -----------------------------------------------------------


def test_normalize_swift_strips_trailing_whitespace_and_crlf() -> None:
    raw = "let x = 1   \r\nlet y = 2\t\r\n"
    out = swiftui_llm.normalize_swift(raw)
    assert out == "let x = 1\nlet y = 2\n"


def test_normalize_swift_enforces_single_trailing_newline() -> None:
    assert swiftui_llm.normalize_swift("a\n\n\n") == "a\n"
    assert swiftui_llm.normalize_swift("a") == "a\n"


def test_normalize_swift_strips_markdown_fences() -> None:
    raw = "```swift\nlet x = 1\n```\n"
    assert swiftui_llm.normalize_swift(raw) == "let x = 1\n"


# --- validate_swift ------------------------------------------------------------


def test_validate_swift_accepts_balanced_view() -> None:
    swiftui_llm.validate_swift(_VALID_BUTTON_SWIFT)  # darf nicht werfen


def test_validate_swift_rejects_empty() -> None:
    with pytest.raises(CodegenError):
        swiftui_llm.validate_swift("   \n")


def test_validate_swift_rejects_unbalanced_braces() -> None:
    with pytest.raises(CodegenError):
        swiftui_llm.validate_swift("func f() { return 1\n")


def test_validate_swift_ignores_braces_in_strings_and_comments() -> None:
    src = """\
// kommentar mit { und ( drin
/* block { ( */
let s = "string mit } und )"
let t = "mehr } )"
func f() -> Int { return 42 }
"""
    swiftui_llm.validate_swift(src)


def test_validate_swift_detects_unterminated_string() -> None:
    with pytest.raises(CodegenError):
        swiftui_llm.validate_swift('let x = "abc\n')


# --- build_prompt + cache key --------------------------------------------------


def test_build_prompt_contains_spec_id_and_props() -> None:
    spec = _load_button()
    prompt = swiftui_llm.build_prompt(spec)  # type: ignore[arg-type]
    assert "@org/button" in prompt
    assert "Button" in prompt
    assert "label" in prompt
    assert "pressed" in prompt
    assert "SwiftUI" in prompt


def test_make_cache_key_is_deterministic_per_spec() -> None:
    spec = _load_button()
    a = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    b = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    assert a == b
    assert a.target == "swiftui"
    assert a.model == swiftui_llm.MODEL
    assert a.prompt_version == swiftui_llm.PROMPT_VERSION
    assert a.seed == swiftui_llm.DEFAULT_SEED


def test_make_cache_key_differs_from_react_cache_key() -> None:
    """Wichtig: SwiftUI- und React-Cache-Keys derselben Spec dürfen sich nie kreuzen."""
    from speccify_core.codegen import react_llm

    spec = _load_button()
    react_key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    swiftui_key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    assert react_key != swiftui_key
    assert react_key.target != swiftui_key.target


# --- render via ReplayCacheClient ---------------------------------------------


def test_render_uses_replay_cache_when_entry_present(tmp_path: Path) -> None:
    spec = _load_button()
    key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_SWIFT)

    client = ReplayCacheClient(cache, offline=True)
    result = swiftui_llm.render(spec, client)  # type: ignore[arg-type]
    assert result.text == _VALID_BUTTON_SWIFT
    assert result.cache_key == key


def test_render_offline_miss_raises(tmp_path: Path) -> None:
    spec = _load_button()
    cache = ReplayCache(tmp_path / "cache")
    client = ReplayCacheClient(cache, offline=True)
    with pytest.raises(CacheMissError):
        swiftui_llm.render(spec, client)  # type: ignore[arg-type]


def test_render_to_files_uses_pascal_case_path(tmp_path: Path) -> None:
    spec = _load_button()
    key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_SWIFT)
    client = ReplayCacheClient(cache, offline=True)

    files, returned_key = swiftui_llm.render_to_files(spec, client)  # type: ignore[arg-type]
    assert list(files.keys()) == ["org/Button.swift"]
    assert files["org/Button.swift"].decode("utf-8") == _VALID_BUTTON_SWIFT
    assert returned_key == key


def test_render_rejects_invalid_swift(tmp_path: Path) -> None:
    spec = _load_button()
    key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, "func broken() { return 1\n")  # fehlende `}`
    client = ReplayCacheClient(cache, offline=True)
    with pytest.raises(CodegenError):
        swiftui_llm.render(spec, client)  # type: ignore[arg-type]


def test_render_strips_markdown_fences_from_llm(tmp_path: Path) -> None:
    spec = _load_button()
    key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, f"```swift\n{_VALID_BUTTON_SWIFT}```\n")
    client = ReplayCacheClient(cache, offline=True)
    result = swiftui_llm.render(spec, client)  # type: ignore[arg-type]
    assert result.text == _VALID_BUTTON_SWIFT


# --- Dispatcher render_for_target ---------------------------------------------


def test_dispatcher_supports_swiftui(tmp_path: Path) -> None:
    spec = _load_button()
    key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_SWIFT)
    client = ReplayCacheClient(cache, offline=True)

    rendered = render_for_target(spec, "swiftui", llm_client=client)  # type: ignore[arg-type]
    assert isinstance(rendered, TargetRender)
    assert rendered.cache_key == key
    assert rendered.files["org/Button.swift"].decode("utf-8") == _VALID_BUTTON_SWIFT


def test_dispatcher_swiftui_requires_llm_client() -> None:
    spec = _load_button()
    with pytest.raises(CodegenError):
        render_for_target(spec, "swiftui")  # type: ignore[arg-type]


def test_dispatcher_supported_targets_includes_swiftui() -> None:
    assert "swiftui" in SUPPORTED_TARGETS


def test_dispatcher_uses_cache_key_so_two_runs_are_byte_identical(
    tmp_path: Path,
) -> None:
    spec = _load_button()
    key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_SWIFT)
    client = ReplayCacheClient(cache, offline=True)

    a = render_for_target(spec, "swiftui", llm_client=client)  # type: ignore[arg-type]
    b = render_for_target(spec, "swiftui", llm_client=client)  # type: ignore[arg-type]
    assert a.files == b.files
    assert a.cache_key == b.cache_key
