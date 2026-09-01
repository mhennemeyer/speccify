---
title: MCPs
description: Model-Context-Protocol-Server — wie Agenten und Apps Fähigkeiten jenseits des Dateisystems erreichen.
sidebar:
  order: 4
---

**MCP** (Model Context Protocol) ist ein offener Standard, der einen
KI-Client mit externen Fähigkeiten verbindet. Ein **MCP-Server**
stellt Tools bereit — benannte Operationen mit JSON-Schema-Inputs —
und jeder MCP-Client (ein Terminal-Agent, eine IDE, eine App) kann
sie auflisten und aufrufen. Wo die [Tools](/de/fundamentals/tools/)
dieses Workflows kleine lokale Programme mit stdin/stdout-Vertrag
sind, ist MCP das Wire-Protokoll für Fähigkeiten, die in einem
*laufenden Prozess* leben: eine Datenbank, ein Browser, ein
Ausführungsdienst.

## In diesem Workflow

Die Projektdatei `.mcp.json` deklariert, welche MCP-Server ein
Projekt nutzt. Sie liegt im Repository-Root neben `.agent/`, und der
Agent liest sie wie jede andere Projektdatei:

```json
{
  "mcpServers": {
    "exec": {
      "type": "http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

Hier gilt dieselbe Regel wie für alle `.agent/`-Konfiguration:
**Niemals Secrets in diese Datei** — sie ist Teil des Repositories.
Tokens bleiben im Schlüsselbund oder kommen als Umgebungsreferenz wie
`${MY_TOKEN}` herein.

## Ein echtes Beispiel: der Exec-Server

Das Speccify-Projekt bringt einen lokalen **Exec-MCP-Server** mit —
für Clients, die selbst keine Prozesse starten dürfen. Die
Speccify-App braucht ihn nicht, sie
[führt Aktionen nativ aus](/de/app/actions/) — aber der
Terminal-Agent und jeder gesandboxte Drittclient erreichen dieselben
Kommandos über denselben Server.

```text
 Terminal-Agent ──MCP──▶ ┌─────────────────┐
                         │  Exec-Server    │──▶ führt Kommandos im
 Sandbox-App ──MCP──▶    │  (lokal, :8765) │    Projekt-Root aus, allowlisted
                         └─────────────────┘
```

Der Server stellt drei Tools bereit:

- `run_command` — ein Kommando im Projekt-Root ausführen,
- `run_action` — eine benannte Projekt-Aktion ausführen (definiert in
  `.agent/actions.json`),
- `list_actions` — diese Aktionen auflisten.

Sandboxed Apps dürfen keine beliebigen Prozesse starten, und Agenten
sollten keine ungeprüften Kommandos ausführen — der Exec-Server löst
beides mit einem Mechanismus: einer **Allowlist**
(`.agent/exec-allowlist.json`). Ein Kommando, das kein erlaubtes
Muster deckt, wird nicht ausgeführt, sondern als Pending-Request
geparkt, den der Owner in der Speccify-App einmal (oder dauerhaft)
bestätigt. Das Arbeitsverzeichnis ist fest der Projekt-Root, Läufe
haben ein Timeout, und die Ausgabe streamt live zum Client.

Das Muster verallgemeinert sich: Ein MCP-Server ist eine gute Naht,
wo eine Fähigkeit **eine Implementierung, mehrere Clients und eine
Policy dazwischen** braucht. Das Protokoll transportiert die Aufrufe;
der Server entscheidet, wozu er bereit ist.
