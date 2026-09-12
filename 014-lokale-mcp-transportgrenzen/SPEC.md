---
station: Done
order: 0
created: 2026-09-10
needs_human: false
ready: false
parent: null
---
# Lokale MCP-Server gegen unerlaubte Browserzugriffe absichern

## Why

Beim lokalen App-Startcheck akzeptiert desktop-ui-MCP einen fremden Origin
mit HTTP 200. Der gemeinsame Rust-HTTP-Handler liest weder Origin noch Host,
bevor er Anfragen verarbeitet. Loopback-Bindung allein ist keine vollständige
Grenze gegenüber Browserzugriffen/DNS-Rebinding. Derselbe Core wird von weiteren
MCPs benutzt; betroffene Verträge vor Integrationsausbau prüfen.

## What

Expliziter gemeinsamer Vertrag für Host/Origin, erlaubte Methoden und begrenzte
Anfragegrößen. Native Clients ohne Origin erhalten einen dokumentierten Weg;
Browser-Origin- und Host-Allowlist eng festlegen. Vorhandene Exec-/SSE-Clients
und konfigurierbare Loopback-Ports berücksichtigen. Keine neue Authentifizierung
oder entfernte Bereitstellung allein durch diese Spec freigeben.

## Acceptance

- Fremder Origin und unerlaubter Host werden vor RPC-/Stream-Verarbeitung abgewiesen.
- Gültiger lokaler Client durchläuft initialize, initialized und tools/list.
- Erlaubte Browseroberflächen funktionieren nur mit ausdrücklich vereinbarter Origin.
- Zu große Requests und unerlaubte Methoden führen zu begrenzten, verständlichen Fehlern.
- Tests belegen, dass abgewiesene Requests keine Tool-Ausführung auslösen.

## Decisions

- Ausgangspunkt `crates/mcp-core/src/lib.rs::handle_http_request`.
- GET-Test an laufender App belegt nur fehlende Origin-Abweisung, keinen
  vollständigen Exploit. Handler-Code zeigt dieselbe fehlende Prüfung vor POST.
- 2026-09-10: Fortsetzungsauftrag und freie Update-Neustarts ausdrücklich erteilt;
  kleinste Backlog-Order gemäß spec-next. Andere bereits bereitgestellte Specs
  verbleiben bei menschlicher Abnahme; Umsetzung dieser Sitzung nur Spec 014.
- D1: Alle vier Rust-HTTP-Server verwenden dieselbe Eingangsprüfung. Binden
  weiter an 127.0.0.1, Host nur 127.0.0.1/localhost mit tatsächlichem Listen-Port.
  Keine DNS-Auflösung und kein Vertrauen in Forwarded-/X-Forwarded-Host-Header.
- D2: Aktuelle Clients sind nativ (CLI/MCP-Hosts, Swift-Client, Rust-Adapter).
  Browser-Origin-Allowlist bleibt leer: jeder vorhandene Origin, auch null und
  localhost, wird abgelehnt. Keine CORS-Freigabe; Browserintegrationen benötigen
  eine spätere ausdrückliche, getestete Freigabe statt pauschaler localhost-Ausnahme.
- D3: POST benötigt application/json (Parameter erlaubt), maximal 1 MiB Body;
  auch chunked wird beim Lesen begrenzt. Mehrdeutiges Framing wird abgewiesen.
  GET-Banner und Pfadsemantik bleiben kompatibel; andere Methoden erhalten 405.
- D4: stdio, Tool-Allowlist, Prozessverwaltung und Protokollversion unverändert.
  Keine Authentifizierungs- oder vollständige DoS-/MCP-Konformitätszusage.

## Tasks

- [x] Aktuelle Client-/Host-/Origin-Verträge und betroffene Server erfassen.
- [x] Gemeinsame Eingangsprüfung implementieren und Negativtests ergänzen.
- [x] Handshake und Exec/SSE-Regressionsprüfungen ausführen.
- [x] Geprüften lokalen Build abgestimmt übernehmen und Bestandsbuch aktualisieren.

## Verification

### 2026-09-10 · Iteration 1 · open

- Skills: spec-next; speccify (Suche mcp ohne Treffer); mcp-client-streamable-http
  (Schritt 10), sandboxed-mac-app-local-exec (Transport-Sicherheitsgrenzen).
  Kein Client-/App-Store-Umbau. Tool verify-stream besitzt entgegen dem Skilltext
  keine macos.sh-Implementierung; reproduzierbare Rust- und HTTP-Regressionsprüfungen
  prüfen hier den realen gemeinsamen Serverpfad, ohne globalen Tool-Prüfstatus zu ändern.
- Primärquelle geprüft: [MCP-Transport 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports),
  Origin-Prüfung und Loopback-Bindung. Zusätzliche Host-/Body-Grenzen sind der
  lokale Sicherheitsvertrag dieser Spec, kein Versionswechsel des Protokolls.

- 2026-09-10 12:43 UTC: GET mit `Origin: https://evil.example` an
  http://127.0.0.1:18768 antwortet 200. Keine Tool-Ausführung beim Negativprobeversuch.
- Codeprüfung: Loopback-Bindung vorhanden; Origin-/Host-Prüfung im Handler fehlt.
- Hinweis aus der Transport-Checkliste des Skills `mcp-client-streamable-http`.
  Historischer Ausgangsbefund vor Umsetzung, keine vollständige Konformitätsabnahme.

### 2026-09-10 · Iteration 1 · ok

- `cargo test --workspace --quiet`: 97 bestanden, 1 bestehender ignorierter Test.
  Davon mcp-core 14 Tests mit echten kurzlebigen TCP-Listenern: Origin/Host,
  doppelte Header, falsche Methoden/Medientypen, Parsefehler/UTF-8, verkürzte Bodies,
  exakte 1-MiB-Grenze und darüber (fest/chunked), 413 vor 100-continue,
  positive native Handshakes/RPC/Streams. Zähler belegen kein Tool-/Stream-Dispatch
  bei Ablehnung. Vorhandene Exec-Timeout-/Disconnect-/Output-Tests ebenfalls grün.
- `scripts/exec_mcp_contract.py`: bisheriges Bundle auf isoliertem Port 19865
  gegen neuen Exec-Server auf 19866 verglichen; alle 28 Szenarien identisch,
  inklusive Pending-Dateien, einmaliger Allowlist-Freigabe, JSON-RPC und SSE.
  Keine VM oder externen Dienste verwendet. Beide Testserver danach beendet.
- `scripts/test_mcp_http_boundary.py`: neuer Exec-Testserver und aktualisierte
  App geprüft. Initialize/initialized/tools/list funktionieren; fremder Origin
  (GET/POST), null/localhost-Origin, fremder Host/Port → 403, Text-POST → 415,
  DELETE/OPTIONS → 405, übergroßer deklarierter Body → 413. Kein tools/call
  im Live-Smoke-Test; keine Tool-Ausführung im Nutzerprojekt.
- `cargo fmt --check`, Ruff-Check/Format des Smoke-Tests, `git diff --check`
  und Frontend-Typecheck/Build im App-Build grün. Bekannte Chunkgrößenwarnung bleibt.
- `scripts/build_sidecars.sh --debug` baut alle drei MCPs neu. Danach regulärer
  App-Quit und `scripts/dev.sh --app --prepared --ui-port=18768`: Exit 0.
  14:25 UTC App PID 83285 auf 127.0.0.1:18768, kein Vite nötig. App-Binary und
  alle drei gebündelten Sidecars entsprechen dem neuen Build (cmp Exit 0).
  Gespeicherte Projektfenster wieder geöffnet; App bleibt zur Nutzung verfügbar.
- Restgrenzen bewusst erhalten: keine lokale Client-Authentifizierung, keine
  Header-/Slow-client-/Verbindungslimits, historisches GET-Banner, kein pauschales
  MCP-Konformitätsversprechen. Browserintegration ist ohne eigene Freigabe gesperrt.

## Questions

- Browserfreigaben: derzeit keine erforderlich/erteilt (D2); kein Umsetzungsblocker.
