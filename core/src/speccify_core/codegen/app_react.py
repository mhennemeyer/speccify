"""Deterministisches React/Vite-Projekt aus einer `kind: app`-Spec (Phase P4).

`speccify build` erzeugt hier ein vollständiges, lauffähiges Projekt: Vite +
Hash-Router + verdrahtete Screens. Das Scaffold ist templatebasiert und ohne
LLM — nur die Komponenten-Implementierungen kommen wahlweise aus dem
(LLM-)Codegen oder als deterministische Mocks (`--mocks`).

Entscheidungen (Plan P4):

* **D12** — kein `react-router`: das Projekt bringt einen ~40-zeiligen
  Hash-Router mit. Damit läuft es mit `react`/`react-dom`/`vite` und die
  Route-Semantik steht lesbar im generierten Code.
* **D13** — genau ein Zustandsknoten: `src/App.tsx` hält Wiring-State *und*
  Route und rendert nur den Knoten der aktiven Route. Die Wiring-Semantik ist
  dieselbe wie im Composite-Mock (`set` → State, `emit` → eigener Callback),
  ergänzt um `navigate`.
* **D14** — das Scaffold ist in beiden Füllungen byte-identisch. Der Unterschied
  liegt allein unter `src/components/`: mit `--mocks` die Mock-Closure plus ein
  Re-Export je Komponente (der Import-Swap aus dem P2-Vertrag, sichtbar
  gemacht), ohne `--mocks` die generierte Implementierung.

Determinismus: reiner Funktions-Output aus Spec-Bytes + Kind-Spec-Bytes +
`APP_TEMPLATE_VERSION`. Keine Zeit-, Zufalls- oder Umgebungswerte.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from speccify_core.api import ComponentApi, component_api
from speccify_core.app import AppSpec, parse_app
from speccify_core.codegen.mock_react import (
    _camel,
    _component_name,
    _event_prop_name,
    _payload_ts,
    _source_expr,
    _ts_literal,
    render_mock_closure,
)
from speccify_core.composition import (
    Composition,
    CompositionResolutionError,
    TreeNode,
    parse_composition,
    resolve_composition_children,
)
from speccify_core.registry import Registry, Spec

APP_TEMPLATE_SET: str = "p4-app-react"
APP_TEMPLATE_VERSION: str = "0.1.0"
TARGET: str = "react"

COMPONENT_DIR = "src/components"

# Versions-Pins des Scaffolds — bewusst dieselben Ranges wie in `apps/composer`,
# damit ein Build im Repo-Workspace ohne frische Auflösung installierbar ist.
_DEPENDENCIES: dict[str, str] = {"react": "^19.0.0", "react-dom": "^19.0.0"}
_DEV_DEPENDENCIES: dict[str, str] = {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "~5.6.3",
    "vite": "^6.0.7",
}


class AppCodegenError(RuntimeError):
    """App-Projekt konnte nicht erzeugt werden (Spec-Struktur, Auflösung)."""


@dataclass(frozen=True)
class AppRender:
    """Ergebnis eines Projekt-Builds: `{relativer_pfad: bytes}` + Template-Pin."""

    files: dict[str, bytes]
    template_set: str
    template_version: str
    mocks: bool


# --- Namens-Helfer ------------------------------------------------------------


def _project_name(spec_id: str) -> str:
    """`@org/demo-app` → `org-demo-app` (npm-tauglicher Paketname)."""
    return spec_id.lstrip("@").replace("/", "-")


def _env_key(name: str) -> str:
    """`api_base_url` → `VITE_API_BASE_URL` (Vite exponiert nur `VITE_`-Variablen)."""
    return f"VITE_{name.upper()}"


def _css_var(token: str) -> str:
    return f"--{token.replace('_', '-')}"


def _component_import(spec_id: str) -> str:
    scope = spec_id.lstrip("@").split("/", 1)[0]
    return f"./components/{scope}/{_component_name(spec_id)}"


def _component_path(spec_id: str) -> str:
    scope = spec_id.lstrip("@").split("/", 1)[0]
    return f"{COMPONENT_DIR}/{scope}/{_component_name(spec_id)}.tsx"


def _text(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def _json_file(data: Any) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8")


# --- Scaffold-Dateien ---------------------------------------------------------


def _package_json(spec: Spec) -> bytes:
    return _json_file(
        {
            "name": _project_name(spec.spec_id),
            "version": str(spec.version),
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc --noEmit && vite build",
                "preview": "vite preview",
                "typecheck": "tsc --noEmit",
            },
            "dependencies": dict(_DEPENDENCIES),
            "devDependencies": dict(_DEV_DEPENDENCIES),
        }
    )


def _tsconfig() -> bytes:
    return _json_file(
        {
            "compilerOptions": {
                "target": "ES2022",
                "lib": ["ES2022", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "moduleResolution": "bundler",
                "jsx": "react-jsx",
                "strict": True,
                "noEmit": True,
                "skipLibCheck": True,
                "types": ["vite/client"],
            },
            "include": ["src"],
        }
    )


def _vite_config() -> bytes:
    return _text(
        [
            'import react from "@vitejs/plugin-react";',
            'import { defineConfig } from "vite";',
            "",
            "// Relative Basis: das Bundle läuft auch aus einem Unterpfad oder",
            "// aus einer Desktop-Shell heraus (file://-nah).",
            "export default defineConfig({",
            '  base: "./",',
            "  plugins: [react()],",
            "});",
        ]
    )


def _index_html(spec: Spec) -> bytes:
    title = str(spec.parsed().get("title", spec.spec_id))
    return _text(
        [
            "<!doctype html>",
            '<html lang="de">',
            "  <head>",
            '    <meta charset="utf-8" />',
            '    <meta name="viewport" content="width=device-width, initial-scale=1" />',
            f"    <title>{title}</title>",
            "  </head>",
            "  <body>",
            '    <div id="root"></div>',
            '    <script type="module" src="/src/main.tsx"></script>',
            "  </body>",
            "</html>",
        ]
    )


def _main_tsx(spec: Spec) -> bytes:
    return _text(
        [
            f"// AUTO-GENERATED by `speccify build` — {APP_TEMPLATE_SET} v{APP_TEMPLATE_VERSION}",
            f"// Spec: {spec.spec_id}@{spec.version}",
            'import * as React from "react";',
            'import { createRoot } from "react-dom/client";',
            "",
            'import App from "./App";',
            "",
            'const container = document.getElementById("root");',
            'if (!container) throw new Error("Kein #root im Dokument.");',
            "createRoot(container).render(",
            "  <React.StrictMode>",
            "    <App />",
            "  </React.StrictMode>,",
            ");",
        ]
    )


def _router_tsx(app: AppSpec) -> bytes:
    return _text(
        [
            f"// AUTO-GENERATED by `speccify build` — {APP_TEMPLATE_SET} v{APP_TEMPLATE_VERSION}",
            "//",
            "// Minimaler Hash-Router (Entscheidung D12): kein Router-Paket, damit das",
            "// Projekt mit react/react-dom/vite läuft und die Route-Semantik lesbar",
            "// im Projekt steht. Ersetzen ist eine lokale Änderung — App.tsx nutzt",
            "// nur `useRoute` und `navigate`.",
            'import * as React from "react";',
            "",
            f"export const START_ROUTE = {_ts_literal(app.start_route.path)};",
            "",
            "export function currentPath(): string {",
            '  const hash = window.location.hash.replace(/^#/, "");',
            '  return hash === "" ? START_ROUTE : hash;',
            "}",
            "",
            "export function navigate(path: string): void {",
            "  window.location.hash = path;",
            "}",
            "",
            "function subscribe(onChange: () => void): () => void {",
            '  window.addEventListener("hashchange", onChange);',
            '  return () => window.removeEventListener("hashchange", onChange);',
            "}",
            "",
            "export function useRoute(): string {",
            "  return React.useSyncExternalStore(subscribe, currentPath, () => START_ROUTE);",
            "}",
        ]
    )


def _theme_css(app: AppSpec) -> bytes:
    lines = [
        f"/* AUTO-GENERATED by `speccify build` — {APP_TEMPLATE_SET} v{APP_TEMPLATE_VERSION} */",
        ":root {",
    ]
    for token, value in app.theme_tokens.items():
        lines.append(f"  {_css_var(token)}: {value};")
    lines.append("}")
    lines.extend(
        [
            "",
            ".speccify-app {",
            "  font-family: system-ui, sans-serif;",
            "  padding: 24px;",
            "  display: grid;",
            "  gap: 16px;",
            "}",
            "",
            ".speccify-unknown-route {",
            "  color: #b91c1c;",
            "}",
        ]
    )
    return _text(lines)


def _env_ts(app: AppSpec) -> bytes:
    lines = [
        f"// AUTO-GENERATED by `speccify build` — {APP_TEMPLATE_SET} v{APP_TEMPLATE_VERSION}",
        "//",
        "// Konfiguration aus `app.env` der Spec. Werte kommen zur Build-Zeit aus",
        "// `import.meta.env` (Vite: nur `VITE_`-Präfix), Defaults stehen in der Spec.",
        "",
        "export const env = {",
    ]
    for entry in app.env:
        default = _ts_literal(entry.default) if entry.default is not None else '""'
        if entry.description:
            lines.append(f"  // {entry.description}")
        lines.append(
            f"  {_camel(entry.name)}: (import.meta.env.{_env_key(entry.name)} as "
            f"string | undefined) ?? {default},"
        )
    lines.append("} as const;")
    return _text(lines)


def _readme(spec: Spec, app: AppSpec, *, mocks: bool) -> bytes:
    parsed = spec.parsed()
    lines = [
        f"# {parsed.get('title', spec.spec_id)}",
        "",
        f"Generiert aus `{spec.spec_id}@{spec.version}` mit `speccify build`",
        f"({APP_TEMPLATE_SET} v{APP_TEMPLATE_VERSION}).",
        "**Nicht von Hand editieren** — die Spec ist die Quelle der Wahrheit.",
        "",
        "```bash",
        "pnpm install",
        "pnpm dev",
        "```",
        "",
        "## Routen",
        "",
        "| Pfad | Screen | Titel |",
        "|---|---|---|",
    ]
    for route in app.routes:
        lines.append(f"| `{route.path}` | `{route.node}` | {route.title or '—'} |")
    lines.extend(
        [
            "",
            "## Komponenten",
            "",
            (
                "Gebaut mit `--mocks`: unter `src/components/` liegen die deterministischen "
                "Mocks. Jede Komponente hat dort einen Re-Export (`<Name>.tsx`), der auf "
                "`<Name>.mock` zeigt — der Import-Swap auf die echte Implementierung ist "
                "genau diese eine Zeile."
                if mocks
                else "Unter `src/components/` liegen die generierten Implementierungen."
            ),
        ]
    )
    if app.env:
        lines.extend(["", "## Konfiguration", "", "| Env | Default |", "|---|---|"])
        for entry in app.env:
            lines.append(f"| `{_env_key(entry.name)}` | `{entry.default or ''}` |")
    return _text(lines)


def _gitignore() -> bytes:
    return _text(["node_modules/", "dist/", ".vite/"])


def _component_barrel(child: Spec) -> bytes:
    component = _component_name(child.spec_id)
    return _text(
        [
            f"// AUTO-GENERATED by `speccify build` — {APP_TEMPLATE_SET} v{APP_TEMPLATE_VERSION}",
            "//",
            "// Import-Swap-Punkt: hier hängt der Mock. Für die echte Implementierung",
            "// zeigt diese Datei auf das generierte Modul — sonst ändert sich nichts.",
            f'export {{ default }} from "./{component}.mock";',
            f'export type {{ {component}Props }} from "./{component}.mock";',
        ]
    )


# --- App.tsx ------------------------------------------------------------------


def _screen_jsx(
    node: TreeNode,
    children: Mapping[str, Spec],
    child_apis: Mapping[str, ComponentApi],
    *,
    indent: str,
) -> list[str]:
    """JSX eines Knotens inkl. Slot-Kindern und Event-Verdrahtung."""
    child_spec = children[node.alias]
    component = _component_name(child_spec.spec_id)
    child_api = child_apis[node.alias]
    lines = [f"{indent}<{component}"]
    lines.append(
        f'{indent}  {{...(collectNodeProps("{node.alias}") as unknown as {component}Props)}}'
    )
    for event in child_api.events:
        handler = _event_prop_name(event.name)
        payload_ts = _payload_ts(event)
        if payload_ts:
            lines.append(f"{indent}  {handler}={{(payload: {payload_ts}) =>")
            lines.append(f'{indent}    fire("{node.alias}.{event.name}", payload)}}')
        else:
            lines.append(f'{indent}  {handler}={{() => fire("{node.alias}.{event.name}", {{}})}}')
    for slot_name, slot_children in node.slots.items():
        lines.append(f"{indent}  {_camel(slot_name)}={{")
        lines.append(f"{indent}    <>")
        for slot_child in slot_children:
            lines.extend(_screen_jsx(slot_child, children, child_apis, indent=indent + "    "))
        lines.append(f"{indent}    </>")
        lines.append(f"{indent}  }}")
    lines.append(f"{indent}/>")
    return lines


def _iter_tree(nodes: tuple[TreeNode, ...]):
    for node in nodes:
        yield node
        for slot_children in node.slots.values():
            yield from _iter_tree(slot_children)


def _app_tsx(
    spec: Spec,
    app: AppSpec,
    composition: Composition,
    children: Mapping[str, Spec],
) -> bytes:
    parsed = spec.parsed()
    own_api = component_api(parsed)
    child_apis = {alias: component_api(child.parsed()) for alias, child in children.items()}
    title = str(parsed.get("title", spec.spec_id))

    lines = [
        f"// AUTO-GENERATED by `speccify build` — {APP_TEMPLATE_SET} v{APP_TEMPLATE_VERSION}",
        f"// Spec: {spec.spec_id}@{spec.version}",
        "//",
        "// Ein Zustandsknoten (Entscheidung D13): Wiring-State + Route liegen hier,",
        "// gerendert wird nur der Screen der aktiven Route.",
        'import * as React from "react";',
        "",
    ]

    seen: set[str] = set()
    for alias in composition.uses:
        child = children[alias]
        component = _component_name(child.spec_id)
        if component in seen:
            continue
        seen.add(component)
        path = _component_import(child.spec_id)
        lines.append(f'import {component} from "{path}";')
        lines.append(f'import type {{ {component}Props }} from "{path}";')
    lines.append('import { navigate, useRoute } from "./router";')
    lines.append('import "./theme.css";')
    lines.append("")

    lines.append("type NodeProps = Record<string, Record<string, unknown>>;")
    lines.append("")
    lines.append("const staticNodeProps: NodeProps = {")
    for node in _iter_tree(composition.tree):
        entries = ", ".join(
            f'"{_camel(name)}": {_ts_literal(value)}' for name, value in node.props.items()
        )
        lines.append(f'  "{node.alias}": {{ {entries} }},')
    lines.append("};")
    lines.append("")

    lines.append("const routeTitles: Record<string, string> = {")
    for route in app.routes:
        lines.append(f"  {_ts_literal(route.path)}: {_ts_literal(route.title or title)},")
    lines.append("};")
    lines.append("")

    lines.append("export default function App(): React.ReactElement {")
    lines.append("  const route = useRoute();")
    lines.append("  const [wired, setWired] = React.useState<NodeProps>({});")
    lines.append("")
    lines.append("  React.useEffect(() => {")
    lines.append(f"    document.title = routeTitles[route] ?? {_ts_literal(title)};")
    lines.append("  }, [route]);")
    lines.append("")
    lines.append("  const nodeProp = (alias: string, prop: string): unknown =>")
    lines.append("    (wired[alias] ?? {})[prop] ?? (staticNodeProps[alias] ?? {})[prop];")
    lines.append("")
    lines.append("  const collectNodeProps = (alias: string): Record<string, unknown> => {")
    lines.append("    const merged: Record<string, unknown> =")
    lines.append("      { ...(staticNodeProps[alias] ?? {}) };")
    lines.append("    for (const [key, value] of Object.entries(wired[alias] ?? {})) {")
    lines.append("      if (value !== undefined) merged[key] = value;")
    lines.append("    }")
    lines.append("    return merged;")
    lines.append("  };")
    lines.append("")

    lines.append("  const fire = (event: string, payload: unknown): void => {")
    lines.append("    void payload;")
    for rule in composition.wiring:
        alias, event_name = rule.when
        lines.append(f'    if (event === "{alias}.{event_name}") {{')
        if rule.set_ is not None:
            set_alias, set_prop = rule.set_
            target_api = child_apis.get(set_alias)
            target_prop = target_api.prop(set_prop) if target_api else None
            if target_prop is None:
                raise AppCodegenError(
                    f"Wiring-Regel setzt '{set_alias}.{set_prop}' — diese Prop gibt es nicht."
                )
            value_expr = _source_expr(rule.to, target_prop.type)
            lines.append(
                f'      setWired((w) => ({{ ...w, "{set_alias}": '
                f'{{ ...(w["{set_alias}"] ?? {{}}), "{_camel(set_prop)}": {value_expr} }} }}));'
            )
        if rule.navigate is not None:
            lines.append(f"      navigate({_ts_literal(rule.navigate)});")
        if rule.emit is not None:
            # Eine App hat keinen Konsumenten — das Event bleibt sichtbar, statt
            # still zu verschwinden.
            own_event = own_api.event(rule.emit)
            payload_note = " mit Payload" if own_event is not None and own_event.payload else ""
            lines.append(
                f'      console.debug("[speccify] {spec.spec_id} emittiert '
                f'{rule.emit}{payload_note}", payload);'
            )
        lines.append("    }")
    lines.append("  };")
    lines.append("")

    lines.append("  return (")
    lines.append('    <div className="speccify-app">')
    for route in app.routes:
        node = next(node for node in composition.tree if node.alias == route.node)
        lines.append(f"      {{route === {_ts_literal(route.path)} ? (")
        lines.extend(_screen_jsx(node, children, child_apis, indent="        "))
        lines.append("      ) : null}")
    known = ", ".join(_ts_literal(route.path) for route in app.routes)
    lines.append(f"      {{![{known}].includes(route) ? (")
    lines.append('        <p className="speccify-unknown-route">Unbekannte Route: {route}</p>')
    lines.append("      ) : null}")
    lines.append("    </div>")
    lines.append("  );")
    lines.append("}")
    return _text(lines)


# --- Öffentliche Render-API ---------------------------------------------------


def render_app_project(
    spec: Spec,
    registry: Registry,
    *,
    mocks: bool = True,
    components: Mapping[str, bytes] | None = None,
) -> AppRender:
    """Rendert das komplette Projekt für eine `kind: app`-Spec.

    `mocks=True` füllt `src/components/` mit der Mock-Closure (plus Re-Export
    je Komponente); `mocks=False` erwartet die generierten Implementierungen in
    `components` (`{"<scope>/<Name>.tsx": bytes}`, wie `render_for_target` sie
    liefert) — der Aufruf des LLM-Codegens bleibt beim Adapter, damit dieses
    Modul netz- und cache-frei bleibt.
    """
    parsed = spec.parsed()
    if str(parsed.get("kind", "")) != "app":
        raise AppCodegenError(
            f"{spec.spec_id}: `speccify build` erwartet `kind: app`, "
            f"nicht '{parsed.get('kind', '')}'."
        )
    app = parse_app(parsed)
    if app is None:
        raise AppCodegenError(f"{spec.spec_id}: `kind: app` ohne `app:`-Block ist nicht baubar.")
    composition = parse_composition(parsed)
    if composition is None:
        raise AppCodegenError(f"{spec.spec_id}: App ohne `composition:` hat keine Screens.")

    try:
        children = resolve_composition_children(composition, registry)
    except CompositionResolutionError as exc:
        raise AppCodegenError(str(exc)) from exc

    missing = [route.node for route in app.routes if route.node not in children]
    if missing:
        raise AppCodegenError(f"{spec.spec_id}: Routen zeigen auf unbekannte Knoten {missing}.")

    files: dict[str, bytes] = {
        "package.json": _package_json(spec),
        "tsconfig.json": _tsconfig(),
        "vite.config.ts": _vite_config(),
        "index.html": _index_html(spec),
        ".gitignore": _gitignore(),
        "README.md": _readme(spec, app, mocks=mocks),
        "src/main.tsx": _main_tsx(spec),
        "src/App.tsx": _app_tsx(spec, app, composition, children),
        "src/router.tsx": _router_tsx(app),
        "src/theme.css": _theme_css(app),
        "src/env.ts": _env_ts(app),
    }

    if mocks:
        for child in children.values():
            for rel_path, data in render_mock_closure(child, registry).files.items():
                files[f"{COMPONENT_DIR}/{rel_path}"] = data
            files[_component_path(child.spec_id)] = _component_barrel(child)
    else:
        if components is None:
            raise AppCodegenError(
                "Ohne `--mocks` müssen die generierten Komponenten übergeben werden."
            )
        for rel_path, data in components.items():
            files[f"{COMPONENT_DIR}/{rel_path}"] = data
        for child in children.values():
            expected = _component_path(child.spec_id)
            if expected not in files:
                raise AppCodegenError(
                    f"Implementierung für {child.spec_id} fehlt (erwartet '{expected}')."
                )

    return AppRender(
        files=dict(sorted(files.items())),
        template_set=APP_TEMPLATE_SET,
        template_version=APP_TEMPLATE_VERSION,
        mocks=mocks,
    )


__all__ = [
    "APP_TEMPLATE_SET",
    "APP_TEMPLATE_VERSION",
    "AppCodegenError",
    "AppRender",
    "render_app_project",
]
