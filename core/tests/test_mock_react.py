"""Tests für den deterministischen React-Mock-Codegen (P2 Stage 3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from speccify_core import (
    LocalRegistry,
    MockUnavailableError,
    ReactToolchainDriver,
    Version,
    render_mock_closure,
    render_mock_files,
)
from speccify_core.codegen.react_llm import validate_tsx

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"


def _registry() -> LocalRegistry:
    return LocalRegistry(FIXTURES)


def _fetch(spec_id: str, version: str = "0.1.0"):
    return _registry().fetch(spec_id, Version.parse(version))


def test_leaf_mock_has_typed_props_events_and_slots() -> None:
    files = render_mock_files(_fetch("@org/button"))
    assert sorted(files) == ["org/Button.mock.tsx"]
    source = files["org/Button.mock.tsx"].decode("utf-8")
    assert "export interface ButtonProps {" in source
    assert "label: string;" in source  # required, kein Default → nicht optional
    assert 'variant?: "primary" | "secondary" | "ghost";' in source
    assert "iconLeading?: React.ReactNode;" in source
    assert "onPressed?: () => void;" in source
    assert "export default function Button(props: ButtonProps)" in source
    assert 'data-speccify-mock="@org/button"' in source
    validate_tsx(source)


def test_event_payload_synthesis_uses_matching_prop() -> None:
    files = render_mock_files(_fetch("@org/text-input"))
    source = files["org/TextInput.mock.tsx"].decode("utf-8")
    # changed{value} nimmt den aktuellen value-Prop als Payload-Quelle.
    assert 'onChanged?.({ value: String(props.value ?? "") })' in source


def test_logic_mock_renders_fixtures_module() -> None:
    files = render_mock_files(_fetch("@org/http-api-client"))
    assert sorted(files) == ["org/HttpApiClient.mock.ts"]
    source = files["org/HttpApiClient.mock.ts"].decode("utf-8")
    assert "export const fixtures = {" in source
    assert '"get_ok"' in source and '"server_error"' in source
    assert "export function fixture(name: FixtureName)" in source


def test_logic_mock_without_fixtures_is_unavailable() -> None:
    spec = _fetch("@org/http-api-client")
    stripped = spec.raw_bytes.decode("utf-8").replace("  fixtures:", "  _fixtures:")
    from speccify_core.registry import Spec

    patched = Spec(
        spec_id=spec.spec_id,
        version=spec.version,
        raw_bytes=stripped.encode("utf-8"),
        path=spec.path,
    )
    with pytest.raises(MockUnavailableError):
        render_mock_files(patched)


def test_composite_closure_renders_children_and_wiring() -> None:
    result = render_mock_closure(_fetch("@org/search-bar"), _registry())
    assert sorted(result.files) == [
        "org/Button.mock.tsx",
        "org/SearchBar.mock.tsx",
        "org/TextInput.mock.tsx",
    ]
    source = result.files["org/SearchBar.mock.tsx"].decode("utf-8")
    assert 'import TextInput from "./TextInput.mock";' in source
    assert "const [wired, setWired] = React.useState<NodeProps>({});" in source
    # set-Regel: changed → value in den State.
    assert '"query_input": { ...(w["query_input"] ?? {})' in source
    # emit-Regel mit props-Quelle: Button-Klick liest den aktuellen Feldwert.
    assert 'query: String(nodeProp("query_input", "value") ?? "")' in source
    # map_to-Forwarding (D3): placeholder → Kind-Prop.
    assert '"placeholder": props.placeholder ?? "Suchen…"' in source
    validate_tsx(source)


def test_mock_render_is_byte_deterministic() -> None:
    first = render_mock_closure(_fetch("@org/search-bar"), _registry())
    second = render_mock_closure(_fetch("@org/search-bar"), _registry())
    assert first.files == second.files
    assert first.template_version == second.template_version


@pytest.mark.conformance
def test_mock_closure_typechecks_via_tsc() -> None:
    driver = ReactToolchainDriver()
    if not driver.is_available():
        pytest.skip("React-Toolchain (node/npm) nicht verfügbar.")
    result = render_mock_closure(_fetch("@org/search-bar"), _registry())
    with tempfile.TemporaryDirectory() as tmp:
        code, output = driver.build(files=result.files, work_dir=Path(tmp))
    assert code == 0, output
