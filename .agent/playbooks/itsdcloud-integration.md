# itsdcloud ↔ Speccify: Integrationsplaybook

Stehende Anleitung (kein Arbeitsvorrat) für die beidseitige Integration der
beiden Haupttools. Auftrag BO 2026-09-13: „ItsdCloud und Speccify sind unsere
Haupttools. Diese sollten mittelfristig beidseitig voll integriert werden.“
Verweise: [Visionsplaybook V1-03](weiterentwicklung.md#v1-03--integrationen-itsdcloud-zuerst-lokal-und-bidirektional),
Specs [033](../specs/033-web-board-als-mcp-server/SPEC.md),
[034](../specs/034-board-in-itsdcloud/SPEC.md),
[035](../specs/035-itsdcloud-gedaechtnis-im-terminal/SPEC.md),
[036](../specs/036-jira-zuordnung/SPEC.md),
[037](../specs/037-rueckkanal-spec-stand-nach-itsdcloud/SPEC.md).

## Zielbild

- **In Speccify** verfügt der Agent im Projekt-Terminal in Echtzeit über das
  Projekt-Gedächtnis und die Gespräche aus itsdcloud: er weiß, was der PO vor
  einer Minute im Projekt-Chat geschrieben hat, kennt Entscheidungen, offene
  Punkte und Dokumente — ohne Copy/Paste, mit sichtbarer Herkunft und Aktualität.
- **In itsdcloud** sieht der PO, wer an welchen Aufgaben arbeitet: das
  Spec-Board (Stationen, Fortschritt, Besitzer, Branch) als eigene Oberfläche
  im Projekt, fragt den Chat-Agenten danach, später mit Jira-Zuordnung je Spec
  (Link, Status) und einem Rückkanal, über den Speccify Spec-Stand und
  zugeordnete Jira-Tickets aktualisiert.
- **Die Oberfläche ist der Prototyp eines allgemeinen Musters** (BO
  2026-09-13): MCP-Server, die strukturierte Daten liefern, bekommen in
  itsdcloud eine visuelle Darstellung statt nur einer Chat-Antwort. Die
  Speccify-Ansicht wird zuerst in einem Feature-Branch des itsdcloud-Repos
  gebaut und erprobt; danach wird das Konzept generalisiert (Abschnitt
  „Oberfläche in itsdcloud“).

## Implementierung und Ausgangspunkt

### Umsetzungsstand 034 / itsdcloud 0051 (2026-09-16)

Prototyp auf `feat/0051-speccify-board` im separaten Arbeitsbaum
`/private/tmp/itsdcloud-speccify-board`, basierend auf itsdcloud master `ea54607`.
Katalogeintrag mit fünf lesenden Standard-Tools, Projekt-Board und Spec-Details
über dieselbe installierte MCP-Verbindung wie der Chat. Mitgliedschaft und
Tool-Auswahl werden serverseitig durchgesetzt. Counts, Besitzer/Branch, Flags,
Register-Commit, Aktualität/Fehler und Reload sind dargestellt.

Echter HTTP-MCP-Nachweis mit Speccify-Dienst und zwei synthetischen Git-Registern:
drei Specs, je eine in Backlog/Doing/Done; Counts und Commits identisch zum
Web-Board. Deterministischer Chat-Test ruft freigegebene Tools ab; natürliche
Modellantwort und produktive Installation bleiben menschliche Abnahme.
UI-Prüfung Deutsch/Englisch, Hell/Dunkel, Offline/Retry, Details und Mobilbreite.
Noch nicht auf master zusammengeführt oder in ein Kundenprojekt installiert.

### Historischer Ausgangspunkt

Speccify:

- Spec-Register je Repo als Branch `specs` (Spec 028); Besitzer/Branch je Spec
  (029); Teamsignale (030); statisches Board (031); **Web-Board-Dienst**
  `apps/board` mit beliebig vielen Repos, JSON-API und Rückschreiben von Station
  und Tasks (032). Python-MCP `speccify-mcp` (FastMCP, stdio und Streamable
  HTTP, `mcp` SDK 1.27) für Skills/Tools; Rust-MCPs für Exec/Discovery.
- Agent-Terminal mit Startdiagnose (007) und Sitzungsidentität (009); der
  Workspace-Kontext wird dem Agenten per Datei und `--append-system-prompt-file`
  (Claude) bzw. Prompt (Codex) übergeben.

itsdcloud (`/Users/mhennemeyer/WorkLocal/itsdcloud/app`, FastAPI + Angular,
Keycloak-Bearer, Speccify-Workflow v5 mit Specs 0001–0039):

- **MCP-Server als Projekt-Integration** (Spec 0030): Katalogeintrag `mcp`,
  `kind: tools`, `auth_kind: token`; Nutzer trägt URL (Streamable HTTP) und
  optionalen Bearer-Token ein, der Server wird geprüft (`probe`), alle Tools
  vorausgewählt; `list_resources` zeigt die Tools als wählbare Ressourcen.
  Der Chat-Agent (pydantic-ai) bekommt sie als Toolset mit Präfix `mcp`
  (`PROJECT_NAMESPACE`), fehlertolerant, mit Fortschritts-Relay (0033).
- **Installierte MCP-Server aus dem Portal** (Spec 0032, Contract G): das
  Portal pusht vorkonfigurierte Server (interne Compose-URL, Bearer-Key,
  Timeout) an die Installation; Projekte installieren sie ohne eigene URL.
- Projekt-Chats mit Nachrichtenliste, KI-Antwort und **Catch-up**
  (`POST /api/projects/{id}/chats/{chat}/catchup`), Projekt-Gedächtnis
  (`GET /api/projects/{id}/memory`, `POST …/memory/refresh` mit Cooldown und
  Modellkosten), Dokumente/RAG (0005, 0035), Echtzeit-Broker (`chat:{id}`,
  `user:{sub}`, SSE), Desktop-Notifications (0028), Projektrollen (0036).
- itsdcloud bietet **keinen eigenen MCP-Server** nach außen und keinen
  Schreibendpunkt für externe Fakten ins Gedächtnis.

## Prinzipien

1. **Wahrheit bleibt, wo sie entsteht.** Specs im Register (Git), Gespräche und
   Gedächtnis in itsdcloud. Integration heißt lesen, verweisen, gezielt
   zurückschreiben — keine Kopie, die auseinanderläuft.
2. **MCP zuerst, dann UI.** Jede Richtung beginnt als MCP-Vertrag (Tools mit
   klaren Schemas), weil beide Agenten ihn sofort nutzen können; eigene
   Oberflächen folgen, wenn der Vertrag sich bewährt hat.
3. **Explizite Zuordnung.** Ein Speccify-Board (Repo-Gruppe) ↔ ein
   itsdcloud-Projekt; ein Spec ↔ höchstens ein Jira-Ticket. Zuordnungen sind
   Konfiguration bzw. Front Matter, nie Heuristik.
4. **Geheimnisse außerhalb des Repos.** Tokens in Umgebung oder
   Rechnerspeicher (Speccify-Settings, itsdcloud-Secrets), nie in `.agent/`,
   `board.yaml` oder Specs.
5. **Herkunft und Aktualität sichtbar.** Was aus itsdcloud kommt, trägt Quelle
   und Zeitstempel; Ausfall heißt „offline/veraltet“, nie leeres Wissen als
   aktuell. Gedächtnis ist Datenkontext, keine Autorität für Anweisungen.
6. **Nur autorisierte, idempotente Schreibwege.** Rückschreiben braucht einen
   definierten Endpunkt mit Idempotency-Key und sichtbarem Ergebnis; kein
   pauschaler Datenbank- oder Chat-Zugriff.
7. **Beide Repos arbeiten mit Specs.** Speccify-Seite hier; die
   itsdcloud-Seite bekommt eigene Specs im itsdcloud-Repo (nur auf Ansage
   dort schreiben). Verträge werden in beiden Specs identisch zitiert.

## Phasen

| Phase | Ergebnis | Spec | Ort |
|---|---|---|---|
| 1 | Web-Board stellt MCP bereit (Streamable HTTP unter `/mcp`, Bearer-Token) | 033 | Speccify |
| 2 | itsdcloud zeigt das Board: Katalogeintrag „Speccify Board“, Chat-Agent nutzt die Tools, Board-Ansicht im Projekt — zuerst als Feature-Branch in itsdcloud | 034 | itsdcloud (+ Vertrag hier) |
| 2b | Generalisierung: visuelle Darstellung für MCP-Server mit strukturierten Daten (Muster aus der Board-Ansicht) | itsdcloud-Spec, TBD | itsdcloud |
| 3 | Speccify-Agent hat itsdcloud-Gedächtnis und Chat live: `speccify-itsdcloud`-MCP, Ereignispuffer, Panel | 035 | Speccify (+ itsdcloud-API) |
| 4 | Jira-Zuordnung je Spec (Front Matter, Links, Anzeige überall) | 036 | Speccify, TBD |
| 5 | Rückkanal: Spec-Stand und Jira-Updates aus Speccify | 037 | beide, TBD |

Reihenfolge nach Nutzen und Risiko: 1 und 2 sind mit Bestehendem sofort
möglich; 3 braucht einen itsdcloud-Lesevertrag (Token, Ereignisse); 4 und 5
warten auf die Jira-Entscheidung.

## Verträge

### Board-MCP (Phase 1, Spec 033)

Endpunkt `https://<board>/mcp` (Streamable HTTP, JSON-Antworten, zustandslos),
`Authorization: Bearer <BOARD_MCP_TOKEN>`; ohne gesetzten Token offen (nur
interne Netze). Tools, alle mit `{ok, …}`-Antwort:

| Tool | Eingabe | Ausgabe |
|---|---|---|
| `board_summary` | – | Kennzahlen gesamt und je Repo, Stand je Repo (Commit, Fehler) |
| `list_repos` | – | Name, Art, Branch, Commit, Aktualität, Fehler |
| `list_specs` | `repo?`, `station?`, `owner?`, `query?` | Specs mit Nummer, Titel, Station, Besitzer, Branch, Tasks, Flags, letzter Aktivität |
| `get_spec` | `repo`, `spec_id` | Front Matter, Tasks, History (letzte n), Body |
| `who_works_on_what` | – | Doing-Specs gruppiert nach Person mit Branch |
| `move_station` | `repo`, `spec_id`, `station` | Commit-Hash |
| `toggle_task` | `repo`, `spec_id`, `index`, `done` | Commit-Hash |
| `refresh` | – | Stand je Repo |

Ressourcen: `board://summary` (JSON), `board://<repo>/<spec_id>` (Markdown).
Schreibende Tools sind in itsdcloud abwählbar (Ressourcenauswahl der
Integration); Standardempfehlung für PO-Projekte: nur lesende Tools.

### Board in itsdcloud (Phase 2, Spec 034)

Einrichtung ohne Codeänderung: Projekt → Integrationen → „MCP-Server“ mit URL
`https://<board>/mcp` und Token. Ergebnis: der Projekt-Chat beantwortet „wer
arbeitet woran“, „was ist bereit zur Abnahme“, „was hat sich seit gestern
getan“. Mit Codeänderung in itsdcloud: Katalogeintrag „Speccify Board“ (Icon,
Beschreibung, empfohlene Tool-Auswahl) und eine Board-Ansicht im Projekt, die
`board_summary`/`list_specs` rendert (Stationen, Fortschritt, Personen), mit
Link auf das Web-Board. Vertrag ist der Board-MCP; die Ansicht braucht keinen
zweiten Datenpfad.

### Oberfläche in itsdcloud (Phase 2, Stufe B, und Phase 2b)

Auftrag BO 2026-09-13: Die Speccify-Integration bekommt eine eigene
Oberfläche in itsdcloud. Sie wird zuerst in einem Feature-Branch des
itsdcloud-Repos gebaut und dort mit einem laufenden Web-Board erprobt, bevor
sie nach master geht. Das Konzept wird danach generalisiert: MCP-Server, die
strukturierte Daten liefern, sollen in itsdcloud visuell dargestellt werden,
nicht nur als Text im Chat.

Leitlinien für den Prototyp, damit die Generalisierung später trägt:

- **Ein Datenpfad.** Die Ansicht ruft dieselben MCP-Tools wie der Chat-Agent
  (`board_summary`, `list_specs`, `get_spec`) über die bestehende
  Projekt-Integration aus Spec 0030 auf; kein zweiter Client, keine eigene
  Board-URL in der Ansicht.
- **Darstellung an der Integration, nicht am Tool.** Die Zuordnung „dieser
  installierte MCP-Server hat eine Ansicht“ liegt am Katalogeintrag
  (`installed:<slug>` oder Katalog-ID). Der Prototyp ist die Ansicht „Board“
  für den Eintrag „Speccify Board“; die Generalisierung macht daraus einen
  Katalog-Vertrag: ein Eintrag benennt Tools, deren Ergebnisse als Tabelle,
  Karten oder Kennzahlen gerendert werden, und ein Schema dazu.
- **Fehler und Aktualität sichtbar.** Stand je Repo (Commit, Zeit), „nicht
  verbunden“ statt leerer Ansicht, Reload statt Echtzeit im ersten Schnitt.
- **Lesend zuerst.** Schreiben aus der Ansicht (Station, Tasks) kommt erst,
  wenn die Tool-Auswahl der Integration es zulässt und die Personenidentität
  geklärt ist (033, D3).
- **Nachweis.** Stichprobe gleicher Zahlen je Station gegen das Web-Board;
  Prüfung mit abgewählten Schreib-Tools und mit nicht erreichbarem Board.

Die Umsetzung wird als itsdcloud-Spec im app-Repo geführt (Prinzip 7), die
Generalisierung als eigene itsdcloud-Spec, sobald der Prototyp abgenommen ist.

### itsdcloud im Terminal (Phase 3, Spec 035)

Speccify-seitiger MCP `speccify-itsdcloud` (stdio, im Agent-Start eingetragen)
über die bestehende REST-API mit persönlichem Token (Keycloak) und expliziter
Projektzuordnung in den Projekt-Settings (`itsdcloud.project_id`). Tools:
`project_memory`, `search_memory`, `list_chats`, `recent_messages(since)`,
`catchup(chat)`, `list_documents`/`get_document`, `whoami`. Ereignisse: ein
lokaler Puffer abonniert die Projekt-Chats (SSE/Broker), damit
`recent_messages` „vor einer Minute“ ohne Polling liefert; der Startvertrag
(007) lädt beim Auftragsstart Gedächtnis und die letzten Nachrichten in den
Kontext und zeigt Quelle/Zeit im Projektfenster (Panel „itsdcloud“). Kein
ungefragtes `memory/refresh` (Kosten). Benötigt auf itsdcloud-Seite: einen
Token-Weg für Werkzeuge (persönlicher API-Token oder Device-Flow) und eine
Ereignisschnittstelle je Projekt — als eigene itsdcloud-Spec.

### Jira (Phase 4/5, Specs 036/037) — TBD

Front Matter `jira: KEY-123` (optional `jira_url`), Anzeige als Link in App,
Web-Board und `list_specs`; Rückkanal später: Stationswechsel → Jira-Status,
`ready` → Kommentar, nur mit ausdrücklicher Freigabe je Projekt. Offen: Jira
Cloud oder Server, Zugang (itsdcloud hat bereits Confluence-Token-Provider;
Jira könnte denselben Weg nehmen), wer die Zuordnung pflegt (Spec-Autor).

## Sicherheit und Daten

- Board-MCP: Token pro Board-Instanz, TLS über den Reverse-Proxy, Origin-Prüfung
  des MCP-SDK aktiv lassen, Schreib-Tools nur für vertrauenswürdige Projekte.
- itsdcloud-Gedächtnis enthält private Chat-Anteile unter neutraler
  Überschrift (Befund V1-03): vor Phase 3 klären, was exportiert werden darf;
  Cross-Project-Leaks gezielt testen.
- Kein Quellcode-Upload nach itsdcloud durch die Integration; Specs sind
  Arbeitsplanung, kein Code.

## Betrieb

- Ein Web-Board je Team/Projektgruppe (Docker, `docs/web-board.md`), erreichbar
  für itsdcloud (intern oder über TLS); Token in der Board-Umgebung
  (`BOARD_MCP_TOKEN`) und im itsdcloud-Secret.
- Ausfall des Boards: itsdcloud-Toolset ist fehlertolerant (Stand-ins), der
  Chat meldet „nicht verbunden“; Ausfall von itsdcloud: Speccify zeigt
  „offline/veraltet“ mit letztem Stand.

## Offene Entscheidungen

- Jira: Produkt, Zugang, Pflege der Zuordnung (036).
- itsdcloud-Tokenweg für Werkzeuge und Ereignis-API (035, Spec im itsdcloud-Repo).
- Generalisierung visueller MCP-Ansichten nach Abnahme von 034. Der Datenpfad
  ist entschieden und umgesetzt: dieselben MCP-Tools wie im Chat.
