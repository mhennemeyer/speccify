# QA-Brücke: die laufende App von außen prüfen

Spec 039. Speccify ist eine Tauri-App; auf macOS gibt es keinen WebDriver
dafür und der WKWebView spricht kein Chrome-DevTools-Protokoll. Playwright
kann deshalb nur das Mock-UI (`apps/desktop/dev/mock.html`) steuern. Für
Abnahmen gegen die **gebündelte App** mit echten Rust-Befehlen, echtem
PTY-Terminal und echter Zwischenablage gibt es die QA-Brücke: einen
Loopback-HTTP-Endpunkt im App-Prozess, den das Prüfwerkzeug
`speccify-qa` anspricht.

## Einschalten

Die Brücke ist **nie im Normalbetrieb aktiv**. Sie läuft nur, wenn die App
mit Flag oder Umgebungsvariable startet:

```sh
./scripts/dev.sh --app --prepared --skip-engine --ui-port=18768 --qa-bridge=18769
# oder direkt: Speccify.app/Contents/MacOS/speccify-desktop --qa-bridge=18769
# oder: SPECCIFY_QA_BRIDGE=18769 (Token optional über SPECCIFY_QA_TOKEN)
```

Beim Start schreibt die App `<tmp>/speccify-qa-bridge.json` (Rechte 0600)
mit `url`, `port`, `token`, `pid` und der Adresse des Desktop-UI-MCP. Ohne
`SPECCIFY_QA_TOKEN` erzeugt sie ein zufälliges Token; auf macOS vererbt
`open` die Shell-Umgebung nicht, deshalb ist die Datei der verlässliche Weg.

## Vertrag

Alle Anfragen: `Authorization: Bearer <token>`, Host `127.0.0.1` oder
`localhost`; sonst 401/403. Anfragekörper JSON, höchstens 1 MiB.

| Route | Körper | Antwort |
|---|---|---|
| `GET /health` | — | `{ok, pid, version}` |
| `GET /windows` | — | `{ok, windows:[{label,title,visible,focused,position,size,scale}]}` |
| `POST /eval` | `{window, js, timeout_ms?}` | `{ok:true, value}` oder `422 {ok:false, error}`; `504` bei Timeout |
| `POST /invoke` | `{window, command, args?}` | Ergebnis des Tauri-Befehls wie `/eval` |
| `POST /focus` | `{window}` | `{ok:true}` |
| `POST /screenshot` | `{window}` | PNG (macOS, `screencapture -R` mit dem Fensterrechteck); sonst 501 |

`js` ist ein **Funktionsrumpf**: `return document.title`, `await` erlaubt.
Das Ergebnis muss JSON-fähig sein, sonst kommt seine String-Form. Fensterabfragen
und `eval` laufen auf dem Hauptthread; steht der (z. B. ein macOS-Systemdialog),
antwortet die Brücke nach fünf Sekunden mit `503` statt zu hängen.

Fensterlabels: `main` (Dashboard), `project-<hash>` (Projektfenster; die
Wurzel liefert `/invoke` mit `project_current`), `workspace-*`, `ask-<n>`
(Frage-Popups aus Spec 038; deren sandboxed iframe ist von außen nicht lesbar).

## Frontend-Haken

`window.__speccifyQa` (in jedem Fenster, ohne Brücke wirkungslos):

- `terminalText()` — sichtbarer Puffer des Agent-Terminals dieses Fensters als
  Text, `null` ohne Terminal.
- `terminalReady()` — ob ein Terminal Aufträge annimmt (Spec 011).

Klicks und Eingaben laufen über das DOM (`element.click()`, Wert setzen und
`input`-Event); dafür tragen die Bedienflächen Rollen, `aria-label` und
`data-*`-Attribute (`data-spec-card`, `data-station`, `data-terminal-ready`).

## Nutzung aus speccify-qa

```sh
cd ../speccify-qa
uv run python -m speccify_qa.cli env                       # zeigt „qa_bridge: erreichbar“
uv run python -m speccify_qa.cli abnahme run speccify-011-auftrag
```

Der Adapter `speccify_qa.bridge` findet Adresse und Token selbst; die
Page-Objects in `speccify_qa.pages` (Board, Auftrags-Dialog, Terminal) kapseln
das DOM-Wissen. Läuft die App ohne Brücke, überspringen die Stufe-2-Tests mit
dem Startbefehl.

## Grenzen

- Eine Brücke pro App-Instanz; die Single-Instance-Regel bleibt.
- Screenshots brauchen auf macOS die Freigabe „Bildschirmaufnahme“ für die App.
- Kein Zugriff in sandboxed iframes (Ad-hoc-UI), keine Aufzeichnung.
