"""Tests für `speccify_core.codegen.react_llm` + Dispatcher (Phase 1b Step 4)."""

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
from speccify_core.codegen import react_llm
from speccify_core.registry import LocalRegistry, Version

REGISTRY_FIXTURES = Path(__file__).resolve().parents[2] / "registry-fixtures"


def _load_button() -> object:
    registry = LocalRegistry(REGISTRY_FIXTURES)
    return registry.fetch("@org/button", Version.parse("0.1.0"))


_VALID_BUTTON_TSX = """\
import React from "react";

export interface ButtonProps {
  label: string;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  iconLeading?: string;
  onPressed?: () => void;
  onLongPressed?: () => void;
}

const Button: React.FC<ButtonProps> = (props) => {
  return <div className="button">{props.label}</div>;
};

export default Button;
"""


# --- normalize_tsx -------------------------------------------------------------


def test_normalize_tsx_strips_trailing_whitespace_and_crlf() -> None:
    raw = "const x = 1;   \r\nconst y = 2;\t\r\n"
    out = react_llm.normalize_tsx(raw)
    assert out == "const x = 1;\nconst y = 2;\n"


def test_normalize_tsx_enforces_single_trailing_newline() -> None:
    assert react_llm.normalize_tsx("a\n\n\n") == "a\n"
    assert react_llm.normalize_tsx("a") == "a\n"


def test_normalize_tsx_strips_markdown_fences() -> None:
    raw = "```tsx\nconst x = 1;\n```\n"
    assert react_llm.normalize_tsx(raw) == "const x = 1;\n"


# --- validate_tsx --------------------------------------------------------------


def test_validate_tsx_accepts_balanced_component() -> None:
    react_llm.validate_tsx(_VALID_BUTTON_TSX)  # darf nicht werfen


def test_validate_tsx_rejects_empty() -> None:
    with pytest.raises(CodegenError):
        react_llm.validate_tsx("   \n")


def test_validate_tsx_rejects_unbalanced_braces() -> None:
    with pytest.raises(CodegenError):
        react_llm.validate_tsx("const f = () => { return 1;\n")


def test_validate_tsx_ignores_braces_in_strings_and_comments() -> None:
    src = """\
// kommentar mit { und ( drin
/* block { ( */
const s = "string mit } und )";
const t = 'mehr } )';
const u = `template } )`;
const f = () => 42;
"""
    react_llm.validate_tsx(src)


def test_validate_tsx_detects_unterminated_string() -> None:
    with pytest.raises(CodegenError):
        react_llm.validate_tsx('const x = "abc;\n')


# --- build_prompt + cache key --------------------------------------------------


def test_build_prompt_contains_spec_id_and_props() -> None:
    spec = _load_button()
    prompt = react_llm.build_prompt(spec)  # type: ignore[arg-type]
    assert "@org/button" in prompt
    assert "Button" in prompt
    assert "label" in prompt
    assert "pressed" in prompt


def test_make_cache_key_is_deterministic_per_spec() -> None:
    spec = _load_button()
    a = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    b = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    assert a == b
    assert a.target == "react"
    assert a.model == react_llm.MODEL
    assert a.prompt_version == react_llm.PROMPT_VERSION
    assert a.seed == react_llm.DEFAULT_SEED


# --- render via ReplayCacheClient ---------------------------------------------


def test_render_uses_replay_cache_when_entry_present(tmp_path: Path) -> None:
    spec = _load_button()
    key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TSX)

    client = ReplayCacheClient(cache, offline=True)
    result = react_llm.render(spec, client)  # type: ignore[arg-type]
    assert result.text == _VALID_BUTTON_TSX
    assert result.cache_key == key


def test_render_offline_miss_raises(tmp_path: Path) -> None:
    spec = _load_button()
    cache = ReplayCache(tmp_path / "cache")
    client = ReplayCacheClient(cache, offline=True)
    with pytest.raises(CacheMissError):
        react_llm.render(spec, client)  # type: ignore[arg-type]


def test_render_to_files_uses_pascal_case_path(tmp_path: Path) -> None:
    spec = _load_button()
    key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TSX)
    client = ReplayCacheClient(cache, offline=True)

    files, returned_key = react_llm.render_to_files(spec, client)  # type: ignore[arg-type]
    assert list(files.keys()) == ["org/Button.tsx"]
    assert files["org/Button.tsx"].decode("utf-8") == _VALID_BUTTON_TSX
    assert returned_key == key


def test_render_rejects_invalid_tsx(tmp_path: Path) -> None:
    spec = _load_button()
    key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, "const broken = () => { return 1;\n")  # fehlende `}`
    client = ReplayCacheClient(cache, offline=True)
    with pytest.raises(CodegenError):
        react_llm.render(spec, client)  # type: ignore[arg-type]


def test_render_strips_markdown_fences_from_llm(tmp_path: Path) -> None:
    spec = _load_button()
    key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, f"```tsx\n{_VALID_BUTTON_TSX}```\n")
    client = ReplayCacheClient(cache, offline=True)
    result = react_llm.render(spec, client)  # type: ignore[arg-type]
    assert result.text == _VALID_BUTTON_TSX


# --- Dispatcher render_for_target ---------------------------------------------


def test_dispatcher_supports_react(tmp_path: Path) -> None:
    spec = _load_button()
    key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TSX)
    client = ReplayCacheClient(cache, offline=True)

    rendered = render_for_target(spec, "react", llm_client=client)  # type: ignore[arg-type]
    assert isinstance(rendered, TargetRender)
    assert rendered.cache_key == key
    assert rendered.files["org/Button.tsx"].decode("utf-8") == _VALID_BUTTON_TSX


def test_dispatcher_react_requires_llm_client() -> None:
    spec = _load_button()
    with pytest.raises(CodegenError):
        render_for_target(spec, "react")  # type: ignore[arg-type]


def test_dispatcher_unknown_target_raises() -> None:
    spec = _load_button()
    with pytest.raises(NotImplementedError):
        render_for_target(spec, "swiftui")  # type: ignore[arg-type]


def test_dispatcher_supported_targets_includes_react() -> None:
    assert "react" in SUPPORTED_TARGETS


def test_dispatcher_uses_cache_key_so_two_runs_are_byte_identical(
    tmp_path: Path,
) -> None:
    spec = _load_button()
    key = react_llm.make_cache_key(spec)  # type: ignore[arg-type]
    cache = ReplayCache(tmp_path / "cache")
    cache.put(key, _VALID_BUTTON_TSX)

    client_a = ReplayCacheClient(cache, offline=True)
    client_b = ReplayCacheClient(cache, offline=True)
    out_a = render_for_target(spec, "react", llm_client=client_a)  # type: ignore[arg-type]
    out_b = render_for_target(spec, "react", llm_client=client_b)  # type: ignore[arg-type]
    assert out_a.files == out_b.files
    assert out_a.cache_key == out_b.cache_key
