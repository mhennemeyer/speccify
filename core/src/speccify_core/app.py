"""App-Belange einer `kind: app`-Spec (Phase P4): Routen, Theme, Env.

Eine App-Spec ist eine ganz normale Komposition — jeder **Top-Level-Knoten
aus `composition.tree` ist ein Screen** (Entscheidung D10). Der `app:`-Block
sagt nur, unter welchem Pfad welcher Knoten erscheint, welche Design-Tokens
das Projekt kennt und welche Konfigurationswerte es erwartet.

Navigation ist eine dritte Wiring-Aktion neben `set`/`emit` (D11):
`navigate: /pfad` wechselt auf die Route mit diesem Pfad. Bewusst ohne
Parameter, Guards oder History-Semantik — die Verdrahtungs-Sprache bleibt
im ersten Schnitt klein.

Dieses Modul bleibt registry-frei: es parst und validiert, es lädt nichts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from speccify_core.composition import CompositionIssue, parse_composition

APP_KIND = "app"


@dataclass(frozen=True)
class Route:
    path: str
    node: str
    title: str | None = None


@dataclass(frozen=True)
class EnvVar:
    name: str
    default: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class AppSpec:
    routes: tuple[Route, ...]
    theme_tokens: dict[str, str] = field(default_factory=dict)
    env: tuple[EnvVar, ...] = ()

    @property
    def start_route(self) -> Route:
        """Erste deklarierte Route — der Einstiegspunkt des Projekts."""
        return self.routes[0]

    def route_for(self, path: str) -> Route | None:
        return next((route for route in self.routes if route.path == path), None)


def parse_app(parsed: dict[str, Any]) -> AppSpec | None:
    """Parst `app:` aus einem Spec-Mapping; `None`, wenn der Block fehlt."""
    raw = parsed.get("app")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("`app:` muss ein Mapping sein.")

    routes: list[Route] = []
    for entry in raw.get("routes") or []:
        if not isinstance(entry, dict) or "path" not in entry or "node" not in entry:
            raise ValueError("Jede Route braucht `path` und `node`.")
        title = entry.get("title")
        routes.append(
            Route(
                path=str(entry["path"]),
                node=str(entry["node"]),
                title=str(title) if title is not None else None,
            )
        )
    if not routes:
        raise ValueError("`app.routes` darf nicht leer sein.")

    theme = raw.get("theme") or {}
    if not isinstance(theme, dict):
        raise ValueError("`app.theme` muss ein Mapping sein.")
    tokens = {str(name): str(value) for name, value in (theme.get("tokens") or {}).items()}

    env: list[EnvVar] = []
    for entry in raw.get("env") or []:
        if not isinstance(entry, dict) or "name" not in entry:
            raise ValueError("Jede `app.env`-Angabe braucht einen `name`.")
        default = entry.get("default")
        description = entry.get("description")
        env.append(
            EnvVar(
                name=str(entry["name"]),
                default=str(default) if default is not None else None,
                description=str(description) if description is not None else None,
            )
        )

    return AppSpec(routes=tuple(routes), theme_tokens=tokens, env=tuple(env))


def validate_app(parsed: dict[str, Any]) -> list[CompositionIssue]:
    """Prüft `app:` gegen `kind`, die Komposition und die Routen-Tabelle.

    Ergänzt `validate_composition` (Typprüfung der Verdrahtung) um die
    App-Regeln; beide Befundlisten sind gleich adressierbar (JSON-Pfad).
    """
    issues: list[CompositionIssue] = []
    kind = str(parsed.get("kind", ""))
    has_app_block = parsed.get("app") is not None

    try:
        app = parse_app(parsed)
    except ValueError as exc:
        return [CompositionIssue("$.app", str(exc))]

    if has_app_block and kind != APP_KIND:
        issues.append(
            CompositionIssue("$.app", f"`app:` ist nur für `kind: app` erlaubt, nicht '{kind}'.")
        )
    if kind == APP_KIND and app is None:
        issues.append(
            CompositionIssue("$.app", "`kind: app` braucht einen `app:`-Block mit `routes`.")
        )

    try:
        composition = parse_composition(parsed)
    except ValueError:
        # Kompositions-Parsefehler meldet bereits `validate_composition`.
        composition = None

    top_level = {node.alias for node in composition.tree} if composition else set()
    paths = [route.path for route in app.routes] if app else []

    if app is not None:
        for index, route in enumerate(app.routes):
            path = f"$.app.routes[{index}]"
            if paths.count(route.path) > 1:
                issues.append(CompositionIssue(path, f"Route-Pfad '{route.path}' ist doppelt."))
            if composition is None:
                issues.append(
                    CompositionIssue(path, "Routen brauchen eine `composition:` mit Screens.")
                )
            elif route.node not in top_level:
                issues.append(
                    CompositionIssue(
                        path,
                        f"Route zeigt auf '{route.node}' — das ist kein Top-Level-Knoten "
                        f"der Komposition (Screens sind Top-Level).",
                    )
                )
        seen_names: set[str] = set()
        for index, env_var in enumerate(app.env):
            if env_var.name in seen_names:
                issues.append(
                    CompositionIssue(
                        f"$.app.env[{index}]", f"Env-Name '{env_var.name}' ist doppelt."
                    )
                )
            seen_names.add(env_var.name)

    # --- navigate-Regeln ------------------------------------------------------
    for index, rule in enumerate(composition.wiring if composition else ()):
        if rule.navigate is None:
            continue
        path = f"$.composition.wiring[{index}].navigate"
        if kind != APP_KIND:
            issues.append(
                CompositionIssue(
                    path, f"`navigate` ist nur in `kind: app` erlaubt, nicht '{kind}'."
                )
            )
            continue
        if app is not None and rule.navigate not in paths:
            known = ", ".join(paths) or "keine"
            issues.append(
                CompositionIssue(
                    path,
                    f"Route '{rule.navigate}' ist nicht deklariert (bekannt: {known}).",
                )
            )

    return issues
