"""Tests für den App-Projekt-Codegen (`speccify build`, Phase P4 Stufe 2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import LocalRegistry, Version
from speccify_core.codegen.app_react import (
    APP_TEMPLATE_SET,
    AppCodegenError,
    render_app_project,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"


def _registry() -> LocalRegistry:
    return LocalRegistry(FIXTURES)


def _demo_app():
    return _registry().fetch("@org/demo-app", Version.parse("0.1.0"))


def _render(**kwargs):
    return render_app_project(_demo_app(), _registry(), **kwargs)


def test_scaffold_files_are_complete() -> None:
    files = _render().files
    assert set(files) >= {
        ".gitignore",
        "README.md",
        "index.html",
        "package.json",
        "src/App.tsx",
        "src/env.ts",
        "src/main.tsx",
        "src/router.tsx",
        "src/theme.css",
        "tsconfig.json",
        "vite.config.ts",
    }


def test_mock_closure_lands_under_components_with_a_swap_point() -> None:
    """`--mocks`: Closure unter src/components + ein Re-Export je Screen (D14)."""
    files = _render().files
    assert "src/components/org/SearchBar.mock.tsx" in files
    # Transitive Kinder des Composite-Screens sind mit dabei.
    assert "src/components/org/Button.mock.tsx" in files
    barrel = files["src/components/org/SearchBar.tsx"].decode()
    assert 'export { default } from "./SearchBar.mock";' in barrel
    assert 'export type { SearchBarProps } from "./SearchBar.mock";' in barrel


def test_mock_bytes_are_the_ones_speccify_mock_writes() -> None:
    """Kein zweiter Mock-Pfad: die Dateien sind byte-identisch zur Mock-Closure."""
    from speccify_core import render_mock_closure

    registry = _registry()
    search_bar = registry.fetch("@org/search-bar", Version.parse("0.1.0"))
    closure = render_mock_closure(search_bar, registry)
    files = _render().files
    for rel_path, data in closure.files.items():
        assert files[f"src/components/{rel_path}"] == data, rel_path


def test_app_tsx_renders_only_the_active_route() -> None:
    app_tsx = _render().files["src/App.tsx"].decode()
    assert "const route = useRoute();" in app_tsx
    for path, component in [
        ("/", "LoginScreen"),
        ("/suche", "SearchBar"),
        ("/kontakt", "ContactForm"),
    ]:
        assert f'{{route === "{path}" ? (' in app_tsx
        assert f"<{component}" in app_tsx
    assert "speccify-unknown-route" in app_tsx


def test_app_tsx_wires_navigate_and_set() -> None:
    app_tsx = _render().files["src/App.tsx"].decode()
    assert 'if (event === "login.login_succeeded") {' in app_tsx
    assert 'navigate("/suche");' in app_tsx
    # Datenfluss über Screens: die Suchanfrage füllt initial_name vor.
    assert '"initialName": String((payload as Record<string, unknown>)["query"] ?? "")' in app_tsx


def test_static_props_and_route_titles_come_from_the_spec() -> None:
    app_tsx = _render().files["src/App.tsx"].decode()
    assert '"search": { "placeholder": "Wonach suchst du?" }' in app_tsx
    assert '"/suche": "Suche",' in app_tsx


def test_theme_tokens_become_css_variables() -> None:
    css = _render().files["src/theme.css"].decode()
    assert "--color-primary: #0f766e;" in css
    assert "--radius-md: 8px;" in css


def test_env_uses_vite_prefixed_variables_with_spec_defaults() -> None:
    env_ts = _render().files["src/env.ts"].decode()
    assert "apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string | undefined)" in env_ts
    assert '?? "http://localhost:8000"' in env_ts


def test_router_pins_the_start_route() -> None:
    router = _render().files["src/router.tsx"].decode()
    assert 'export const START_ROUTE = "/";' in router
    assert 'window.addEventListener("hashchange", onChange);' in router


def test_render_is_deterministic() -> None:
    assert _render().files == _render().files


def test_scaffold_is_identical_for_mocks_and_implementations() -> None:
    """D14: nur `src/components/**` unterscheidet sich zwischen den Füllungen."""
    with_mocks = _render()
    implementations = {
        "org/LoginScreen.tsx": b"export default function LoginScreen() { return null; }\n",
        "org/SearchBar.tsx": b"export default function SearchBar() { return null; }\n",
        "org/ContactForm.tsx": b"export default function ContactForm() { return null; }\n",
    }
    without_mocks = _render(mocks=False, components=implementations)

    def scaffold(files: dict[str, bytes]) -> dict[str, bytes]:
        # README ausgenommen: die sagt bewusst, womit gebaut wurde.
        return {
            path: data
            for path, data in files.items()
            if not path.startswith("src/components/") and path != "README.md"
        }

    assert scaffold(with_mocks.files) == scaffold(without_mocks.files)
    assert (
        without_mocks.files["src/components/org/SearchBar.tsx"]
        == implementations["org/SearchBar.tsx"]
    )
    assert with_mocks.template_set == APP_TEMPLATE_SET
    assert with_mocks.mocks is True and without_mocks.mocks is False


def test_missing_implementation_is_an_error() -> None:
    with pytest.raises(AppCodegenError, match="Implementierung für @org/contact-form fehlt"):
        _render(mocks=False, components={"org/LoginScreen.tsx": b"", "org/SearchBar.tsx": b""})


def test_component_specs_are_rejected() -> None:
    spec = _registry().fetch("@org/button", Version.parse("0.1.0"))
    with pytest.raises(AppCodegenError, match="erwartet `kind: app`"):
        render_app_project(spec, _registry())
