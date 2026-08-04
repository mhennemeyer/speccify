"""Phase P4 Stufe 4: echter Build + Browser-Smoke eines `speccify build`-Projekts.

Der Unit-Teil von P4 prüft *Bytes*. Dieser Test prüft, dass diese Bytes ein
Projekt ergeben, das eine echte Toolchain akzeptiert und ein Browser wie
spezifiziert bedient:

1. `speccify build @org/demo-app --mocks` in ein temporäres Verzeichnis,
2. `tsc --noEmit` + `vite build` mit den Toolchains des Repos,
3. `dist/` ausliefern und mit Playwright durchspielen: Startroute, Navigation
   per Event (`login_succeeded` → `/suche`), Datenfluss über Screens
   (Notiz → `initial_name` im Kontaktformular), unbekannte Route.

Mock-Eigenheit: Event-Payloads eines Mocks kommen aus gleichnamigen Props.
Beobachtbar ist ein Datenfluss deshalb nur, wenn die Quelle eine statische
Prop ist — im Demo trägt der Notiz-Screen (`@org/text-input`) genau die.

Wie Conformance und Visual-Regression läuft das hinter einem Marker
(`pytest -m app_build`) und in einem eigenen CI-Job — es startet externe
Toolchains und ist deutlich langsamer als die Unit-Suite.

Toolchain: statt `pnpm install` im Wegwerf-Projekt (Netz, Minuten) wird
`node_modules` aus `apps/composer` verlinkt. Dort stehen exakt die Pakete, die
das Scaffold pinnt (react 19, vite 6, typescript 5.6, @vitejs/plugin-react).
Fehlt das Verzeichnis, wird der Test übersprungen — nicht rot.
"""

from __future__ import annotations

import http.server
import json
import socket
import subprocess
import threading
from collections.abc import Iterator
from functools import partial
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSER_MODULES = REPO_ROOT / "apps" / "composer" / "node_modules"

pytestmark = pytest.mark.app_build


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=600)


@pytest.fixture(scope="module")
def built_app(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Baut `@org/demo-app` und gibt das `dist/`-Verzeichnis zurück."""
    if not COMPOSER_MODULES.is_dir():
        pytest.skip("toolchain_missing_node_modules: apps/composer/node_modules fehlt (pnpm i)")

    from speccify_cli.commands.build import run_build

    project = tmp_path_factory.mktemp("demo-app-build")
    run_build(
        "@org/demo-app",
        registry_path=REPO_ROOT / "registry-fixtures",
        out_dir=project,
    )
    (project / "node_modules").symlink_to(COMPOSER_MODULES)

    tsc = _run([str(COMPOSER_MODULES / ".bin" / "tsc"), "--noEmit"], project)
    assert tsc.returncode == 0, f"tsc:\n{tsc.stdout}\n{tsc.stderr}"

    vite = _run([str(COMPOSER_MODULES / ".bin" / "vite"), "build"], project)
    assert vite.returncode == 0, f"vite build:\n{vite.stdout}\n{vite.stderr}"

    dist = project / "dist"
    assert (dist / "index.html").is_file()
    return dist


@pytest.fixture(scope="module")
def served(built_app: Path) -> Iterator[str]:
    """Liefert `dist/` über einen lokalen HTTP-Server aus (IPv4, freier Port)."""
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(built_app))

    class Server(http.server.ThreadingHTTPServer):
        address_family = socket.AF_INET
        daemon_threads = True

        def log_message(self, *args: object) -> None:  # pragma: no cover - Ruhe im Log
            pass

    server = Server(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()


_PROBE_JS = """
import { chromium } from "@playwright/test";

const base = process.argv[2];
const out = [];
const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error)));

const screen = async () =>
  page.locator("[data-speccify-mock]").first().getAttribute("data-speccify-mock");

await page.goto(base);
out.push({ step: "start", hash: new URL(page.url()).hash, title: await page.title(),
           screen: await screen() });

await page.locator("button", { hasText: "login_succeeded" }).first().click();
await page.waitForTimeout(150);
out.push({ step: "nach-login", hash: new URL(page.url()).hash, title: await page.title(),
           screen: await screen() });

await page.locator("button", { hasText: "submitted" }).first().click();
await page.waitForTimeout(150);
out.push({ step: "nach-suche", hash: new URL(page.url()).hash, title: await page.title(),
           screen: await screen() });

await page.locator("button", { hasText: "submitted" }).first().click();
await page.waitForTimeout(150);
out.push({ step: "nach-notiz", hash: new URL(page.url()).hash, title: await page.title(),
           screen: await screen(),
           text: await page.locator("[data-speccify-mock='@org/contact-form']").innerText() });

await page.goto(`${base}#/gibtsnicht`);
await page.waitForTimeout(150);
out.push({ step: "unbekannt",
           text: await page.locator(".speccify-unknown-route").innerText() });

await browser.close();
console.log(JSON.stringify({ steps: out, errors }));
"""


def test_generated_app_builds_and_behaves(served: str, tmp_path: Path) -> None:
    probe = REPO_ROOT / "apps" / "composer" / ".speccify-app-probe.mjs"
    probe.write_text(_PROBE_JS, encoding="utf-8")
    try:
        result = _run(["node", str(probe.name), served], probe.parent)
    finally:
        probe.unlink(missing_ok=True)

    if result.returncode != 0 and "executable doesn't exist" in result.stderr:
        pytest.skip("toolchain_missing_chromium: `playwright install chromium` fehlt")
    assert result.returncode == 0, f"probe:\n{result.stdout}\n{result.stderr}"

    report = json.loads(result.stdout.strip().splitlines()[-1])
    steps = {entry["step"]: entry for entry in report["steps"]}

    assert report["errors"] == []
    assert steps["start"]["screen"] == "@org/login-screen"
    assert steps["start"]["title"] == "Anmelden"

    # `navigate` aus der Spec: login_succeeded → /suche.
    assert steps["nach-login"]["hash"] == "#/suche"
    assert steps["nach-login"]["screen"] == "@org/search-bar"
    assert steps["nach-login"]["title"] == "Suche"

    assert steps["nach-suche"]["hash"] == "#/notiz"
    assert steps["nach-suche"]["screen"] == "@org/text-input"

    # Navigation + Datenfluss über Screens in einem Schritt: die Notiz landet
    # als `initial_name` im Kontaktformular.
    assert steps["nach-notiz"]["hash"] == "#/kontakt"
    assert steps["nach-notiz"]["screen"] == "@org/contact-form"
    assert "Speccify" in steps["nach-notiz"]["text"]

    assert "Unbekannte Route" in steps["unbekannt"]["text"]
