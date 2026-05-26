"""Tests für `speccify_core.codegen.angular_llm` + Dispatcher (Phase 3 Stage 3).

Analog zu `test_swiftui_llm.py` (Stage 2) und `test_react_llm.py` (Phase 1b):
inline Replay-Cache via `tmp_path`, keine eingecheckten Golden Renders oder
Replay-Fixtures. Golden Renders mit echten LLM-Outputs sind Stage 4
(Conformance-Runner) vorbehalten.
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
from speccify_core.codegen import angular_llm
from speccify_core.registry import LocalRegistry, Version

REGISTRY_FIXTURES = Path(__file__).resolve().parents[2] / "registry-fixtures"


def _load_button() -> object:
    registry = LocalRegistry(REGISTRY_FIXTURES)
    return registry.fetch("@org/button", Version.parse("0.1.0"))


_VALID_BUTTON_TS = """\
import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-button',
  standalone: true,
  template: `
    <div class="btn">
      <span>{{ label }}</span>
      <span>variant: {{ variant }}</span>
    </div>
  `,
  styles: [`.btn { display: inline-flex; }`],
})
export class ButtonComponent {
  @Input() label: string = '';
  @Input() variant: 'primary' | 'secondary' = 'primary';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() disabled: boolean = false;
  @Input() loading: boolean = false;
  @Input() iconLeading?: string;
  @Output() pressed = new EventEmitter<void>();
  @Output() longPressed = new EventEmitter<void>();
}
"""


# --- normalize_ts -------------------------------------------------------------


def test_normalize_ts_strips_trailing_whitespace_and_crlf() -> None:
    raw = "const x = 1   \r\nconst y = 2\t\r\n"
    out = angular_llm.normalize_ts(raw)
    assert out == "const x = 1\nconst y = 2\n"


def test_normalize_ts_enforces_single_trailing_newline() -> None:
    assert angular_llm.normalize_ts("a\n\n\n") == "a\n"
    assert angular_llm.normalize_ts("a") == "a\n"


def test_normalize_ts_strips_markdown_fences() -> None:
    raw = "```typescript\nconst x = 1;\n```\n"
    assert angular_llm.normalize_ts(raw) == "const x = 1;\n"


# --- validate_ts --------------------------------------------------------------


def test_validate_ts_accepts_balanced_component() -> None:
    angular_llm.validate_ts(_VALID_BUTTON_TS)  # darf nicht werfen


def test_validate_ts_rejects_empty() -> None:
    with pytest.raises(CodegenError):
        angular_llm.validate_ts("   \n")


def test_validate_ts_rejects_unbalanced_braces() -> None:
    with pytest.raises(CodegenError):
        angular_llm.validate_ts("function f() { return 1;\n")


def test_validate_ts_ignores_braces_in_strings_and_comments() -> None:
    src = """\
// kommentar mit { und ( drin
/* block { ( */
const s = "string mit } und )";
const t = 'mehr } )';
const tpl = `template { ( } )`;
function f(): number { return 42; }
"""
    angular_llm.validate_ts(src)


def test_validate_ts_detects_unterminated_string() -> None:
    with pytest.raises(CodegenError):
        angular_llm.validate_ts('const x = "abc\n')


def test_validate_ts_detects_unterminated_template_literal() -> None:
    with pytest.raises(CodegenError):
        angular_llm.validate_ts("const x = `abc\n")


# --- build_prompt + cache key -------------------------------------------------


def test_build_prompt_contains_spec_id_and_props() -> None:
    spec = _load_button()
    prompt = angular_llm.build_prompt(spec)  # type: ignore[arg-type]
    assert "@org/button" in prompt
    assert "ButtonComponent" in prompt
    assert "app-button" in prompt
    assert "label" in prompt
    assert "pressed" in prompt
    assert "@angular/core" in prompt


def test_make_cache_key_is_deterministic_per_spec() -> None:
    spec = _load_button()
    a = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    b = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    assert a == b
    assert a.target == "angular"
    assert a.model == angular_llm.MODEL
    assert a.prompt_version == angular_llm.PROMPT_VERSION
    assert a.seed == angular_llm.DEFAULT_SEED


def test_make_cache_key_differs_from_react_and_swiftui_keys() -> None:
    """Cross-Target-Trennung: Angular-Keys kollidieren nie mit React/SwiftUI."""
    from speccify_core.codegen import react_llm, swiftui_llm

    spec = _load_button()
    react_key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    swiftui_key = swiftui_llm.make_cache_key(spec)  # type: ignore[arg-type]
    angular_key = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    assert angular_key != react_key
    assert angular_key != swiftui_key
    assert angular_key.target == "angular"


# --- render via ReplayCacheClient --------------------------------------------


def test_render_uses_replay_cache_when_entry_present(tmp_path: Path) -> None:
    spec = _load_button()
    key = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TS)

    client = ReplayCacheClient(cache, offline=True)
    result = angular_llm.render(spec, client)  # type: ignore[arg-type]
    assert result.text == _VALID_BUTTON_TS
    assert result.cache_key == key


def test_render_offline_miss_raises(tmp_path: Path) -> None:
    spec = _load_button()
    cache = ReplayCache(tmp_path / "cache")
    client = ReplayCacheClient(cache, offline=True)
    with pytest.raises(CacheMissError):
        angular_llm.render(spec, client)  # type: ignore[arg-type]


def test_render_to_files_uses_kebab_case_path(tmp_path: Path) -> None:
    spec = _load_button()
    key = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TS)
    client = ReplayCacheClient(cache, offline=True)

    files, returned_key = angular_llm.render_to_files(spec, client)  # type: ignore[arg-type]
    assert list(files.keys()) == ["org/button.component.ts"]
    assert files["org/button.component.ts"].decode("utf-8") == _VALID_BUTTON_TS
    assert returned_key == key


def test_render_rejects_invalid_ts(tmp_path: Path) -> None:
    spec = _load_button()
    key = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, "function broken() { return 1;\n")  # fehlende `}`
    client = ReplayCacheClient(cache, offline=True)
    with pytest.raises(CodegenError):
        angular_llm.render(spec, client)  # type: ignore[arg-type]


def test_render_strips_markdown_fences_from_llm(tmp_path: Path) -> None:
    spec = _load_button()
    key = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, f"```typescript\n{_VALID_BUTTON_TS}```\n")
    client = ReplayCacheClient(cache, offline=True)
    result = angular_llm.render(spec, client)  # type: ignore[arg-type]
    assert result.text == _VALID_BUTTON_TS


# --- Dispatcher render_for_target --------------------------------------------


def test_dispatcher_supports_angular(tmp_path: Path) -> None:
    spec = _load_button()
    key = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TS)
    client = ReplayCacheClient(cache, offline=True)

    rendered = render_for_target(spec, "angular", llm_client=client)  # type: ignore[arg-type]
    assert isinstance(rendered, TargetRender)
    assert rendered.cache_key == key
    assert rendered.files["org/button.component.ts"].decode("utf-8") == _VALID_BUTTON_TS


def test_dispatcher_angular_requires_llm_client() -> None:
    spec = _load_button()
    with pytest.raises(CodegenError):
        render_for_target(spec, "angular")  # type: ignore[arg-type]


def test_dispatcher_supported_targets_includes_angular() -> None:
    assert "angular" in SUPPORTED_TARGETS


def test_dispatcher_uses_cache_key_so_two_runs_are_byte_identical(
    tmp_path: Path,
) -> None:
    spec = _load_button()
    key = angular_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TS)
    client = ReplayCacheClient(cache, offline=True)

    a = render_for_target(spec, "angular", llm_client=client)  # type: ignore[arg-type]
    b = render_for_target(spec, "angular", llm_client=client)  # type: ignore[arg-type]
    assert a.files == b.files
    assert a.cache_key == b.cache_key
