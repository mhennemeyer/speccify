---
description: Lebende Produktvision, Ausbauphasen, Architekturvorschläge und Arbeitsweise für Speccify.
---
# Speccify: Produktvision und Weiterentwicklung

Stand: **2026-09-10**. Lebendes Playbook, kein abzuhakender Implementierungsauftrag.

Schnelleinstieg: [Leitbild](#leitbild) · [Phasen](#phasen-und-priorisierung) ·
[Vision 1](#vision-1-bald-umsetzen) · [Vision 2](#vision-2-nach-breiter-interner-nutzung) ·
[Entscheidungen](#offene-produktentscheidungen) ·
[Arbeitsweise](#arbeitsweise-speccify-weiterentwickeln).

## Leseführung und Pflege

- **Dieses Playbook:** vollständige vereinbarte Zielrichtung, offene Entscheidungen,
  vorgeschlagene Ausbauschritte und wiederkehrende Arbeitsweise.
- **[Stand und vollständiger UI-Baum](stand-und-ui.md):** was im aktuellen
  Arbeitsbaum tatsächlich existiert, Belege, Grenzen und Navigationsstruktur.
- **[Specs](../specs/):** einzelne abnehmbare Aufträge samt Aufgaben und Historie.
  Eine Vision ist noch keine Umsetzungsfreigabe oder zugesagte Veröffentlichung.
- **[Website](website.md):** Positionierung, Feature-Reihenfolge und Bildpflege.
  Entscheidung 2026-09-11: Skills/Tool-Verträge zuerst, IDE/Git zuletzt;
  Landingpage plus Features-Seite vorerst Englisch, deutsche Lokalisierung pausiert.
  Spec 023 zeigt das tatsächliche Produkt mit festen öffentlichen Demodaten; Aufnahme
  per lokalem Skill `app-screenshots`, visuelle Freigabe vor Veröffentlichung.
- **[Bestandsaufnahme 006](../specs/006-bestandsaufnahme-agent-terminal/SPEC.md):**
  historischer Ausgangspunkt; wird nicht nachträglich zur heutigen Wahrheit umgeschrieben.

Bei jeder Änderung an Produktumfang, Navigation oder dauerhaftem Arbeitsablauf
beide Playbooks im selben Änderungssatz prüfen. Geänderte Abschnitte, Datum und
betroffene Spec-Verweise aktualisieren; im Bestandsbuch Code, Test und echte
App-Abnahme auseinanderhalten. Release-Stand separat vom lokalen Arbeitsbaum
angeben. Preise und Fremdformate vor ihrer Umsetzung erneut prüfen.

Die Kennungen V1-01 bis V2-02 bleiben als Referenzen stabil. Neue Wünsche hier
ergänzen; abgelöste Entscheidungen mit Grund markieren, nicht still entfernen.
Specs verweisen auf diese Kennungen; dieses Playbook verlinkt zurück, sobald
eine konkrete Spec geschnitten wurde. Keine zweite Task-Liste im Playbook führen.

## Leitbild

Speccify wird das agentenagnostische Arbeitsfenster für nachvollziehbare,
spec-getriebene Entwicklung: vom geöffneten Ordner über Projektwissen, Specs,
Skills, Werkzeuge und Code bis zum gemeinsam sichtbaren Ergebnis.

Das Produkt verbindet die Perspektive des Menschen mit der Arbeitsumgebung
seines gewählten Terminal-Agenten. Es ist weder ein eigener Modellanbieter noch
ein Chatverlauf als alleinige Wissensquelle. Der Mensch kann eingreifen, prüfen
und entscheiden; der Agent bekommt den passenden Projekt- und Auftragskontext.

Dauerhafte Grundlagen:

- Dateien und Git bleiben tragend: Wissen ist lesbar, versionierbar und ohne
  Speccify weiter nutzbar. Lokale Kernarbeit benötigt keinen Speccify-Cloudaccount.
- Specs beschreiben Arbeit; Playbooks beschreiben dauerhaftes Vorgehen und
  Orientierung; Skills sind wiederverwendbares Wissen; Tool-Verträge machen
  plattformspezifische Ausführung explizit und prüfbar.
- Expand → Execute → Evaluate bleibt der Wissenskreislauf. Projekterfahrungen
  werden bewusst generalisiert und ins Team oder in öffentliche Bibliotheken zurückgeführt.
- Desktop, CLI und MCP teilen Verträge statt konkurrierender Wahrheiten.
  Die App unterstützt unterschiedliche Hosts und deren eigene Berechtigungen.
- Zuerst zuverlässiger interner Einsatz auf macOS und Windows; Linux-Buildpfade
  bestehen, sein tatsächlicher Support- und Abnahmestand wird gesondert ausgewiesen.
- Teamfähigkeit ergänzt lokale Arbeit. Dienste und Integrationen dürfen den
  lokalen Kern bei Nichterreichbarkeit nicht unbrauchbar machen.

Erfolg heißt: Ein Kollege öffnet einen Ordner, erkennt Projekte und Arbeitsstand,
startet seinen Agenten mit richtigem Kontext und kann Änderungen bis zur
Abnahme verfolgen — auch über mehrere Repositories und Personen hinweg.

## Phasen und Priorisierung

**Vision 1** ist die nächste Ausbauphase während der internen Nutzung.
**Vision 2** folgt nach einer Phase, in der viele im Team regelmäßig mit Speccify
arbeiten. Das ist eine Reihenfolge, keine Kalender- oder Releasezusage.

Vorschlag für die Umsetzung, noch keine beschlossene Backlog-Neusortierung:

| Schritt | Ergebnis | Bezug |
|---|---|---|
| A: Arbeitsgrundlage absichern | Agent-Start praktisch abnehmen, Workflow/Terminal/Prüfstatus/Kontext konsistent | bestehende Specs 007–012 |
| B: Projektidentität und Teamvertrag | Workspace-/Projekt-/Repo-Modell und Entscheidung zur gemeinsamen Spec-Wahrheit | V1-01, V1-09 |
| C: Interne tägliche Arbeit | Multi-Repo-Oberfläche, itsdcloud zunächst lesend, Source-/Target-Rollen, Feedback-MVP | V1-01/03/05/08 |
| D: Verteilung und Tiefe | Updater produktiv abnehmen; IDE/Git, Memory-Rückkanal, Live-Panels ausbauen | V1-02/03/04/06 |
| E: Erlernbarkeit | 4Notice neu durchspielen, danach umfangreicheres Beispiel | V1-07 |
| F: Öffnung nach außen | fremde Spec-Workflows und Skill-Paketadapter | V2-01/02 |

Updater und Feedback können früher kommen, sobald ihre Voraussetzungen klar
sind. Das neue Tutorial beginnt nicht erst am Ende: veraltete Stellen früh
kennzeichnen, den vollständigen Durchlauf aber gegen den stabilisierten Workflow abnehmen.

## Vision 1: bald umsetzen

### V1-01 — Multi-Repo-Projekte und automatische Erkennung

**Gewünscht:** Einen Ordner öffnen; Speccify erkennt enthaltene Projekte und
Repositories. Jedes Projekt behält eigene Specs, Playbooks und Skills. Dateien,
Git, Playbooks und Skills tragen ihre Projektzugehörigkeit; Board-Karten sind
auch in einer gemeinsamen Übersicht eindeutig gekennzeichnet.

**Entschieden am 2026-09-10 (D-MR-01):** Erkannte Repos werden zunächst als eigene
Projekte angeboten und können anschließend frei fachlich gruppiert werden.
Erster Umsetzungsschnitt: [Spec 015](../specs/015-workspace-projekterkennung/SPEC.md).

**Modell:** Workspace = geöffneter Arbeitsverbund; Projekt = fachlicher
Kontext mit eigenem Wissen; Repository = Git-Grenze. Ein Projekt kann mehrere
Repos haben, ein Workspace mehrere Projekte. Bei der ersten Erkennung wird jedes
Repo zunächst separat angeboten; Zuordnungen bleiben editierbar.
Nicht unbemerkt voraussetzen, dass jeder Unterordner ein Projekt oder jedes
Git-Repo ein anderer fachlicher Kontext ist.

- Erkennung berücksichtigt `.git` als Ordner **und Datei** (Worktrees), vorhandene
  Speccify-Konfiguration und Projektanweisungen. Fremde Workflow-Marker zunächst
  nur erkennen, nicht umschreiben. Kein automatisches `init` beim Öffnen.
- Begrenzte Suche mit Ausschlüssen für Abhängigkeiten/Buildartefakte; verschachtelte
  Repos, Submodule, Symlinks, doppelte Worktrees und Ordner ohne Git explizit behandeln.
- Stabile Projekt-/Repo-IDs statt absolutem Rechnerpfad als Teamidentität.
  `project_id + spec_id` unterscheidet gleich nummerierte Specs; Pfade bleiben lokale Bindungen.
- Umschalter „Alle Projekte / Projekt X“, persistente Auswahl, Projektkennzeichnung
  auf Board, Suchtreffern, Dateien, Git, Skills, Playbooks, Aktionen und Agent-Aufträgen.
- Globale, Workspace- und Projektquellen sichtbar auseinanderhalten. Keine stille
  Verschmelzung gleichnamiger Skills oder Vererbung fremder Schreibrechte.
- Aktionen und Git-Mutationen zeigen Projekt, Repo und Worktree als Ziel.
  Terminal und Kontext dürfen bei einem UI-Wechsel nicht unbemerkt das Projekt wechseln.

**Erster Abnahmeschnitt:** Ein Fixture mit zwei Repos, jeweils einer Spec `001`
und einem gleichnamigen Skill öffnen. Beide erscheinen separat und aggregiert;
eine Änderung an A verändert weder Dateien noch Git-Index noch Kontext von B.
Ein zweiter Worktree wird korrekt erkannt, nicht als unabhängiges Repo dupliziert.

**Bestand 2026-09-11:** Spec 015 implementiert die begrenzte Verbunderkennung und
lokal persistierte Projektgruppen mit getrennten Worktree-Fenstern. Native
Verträge und Grenzen: [Workspace-Vertrag](../../docs/workspaces.md).
Aggregierte Sicht, Herkunfts-Badges und gemeinsame Team-Identitätsbindung fehlen
weiterhin. Die lokale Zuordnung ist kein gemeinsames Team-Register. Basis ist
auch für itsdcloud, Team-Board und spätere Workflow-Adapter erforderlich.

### V1-02 — Autoupdater für die Apps

**Gewünscht:** Interne Nutzer bekommen neue Versionen ohne manuelles Neuinstallieren.

**Bestand:** Tauri-Updater, manuelle Update-Suche unter „Umgebung“, Download und
Installation sowie bedingte Release-Artefakte bestehen. Der eingecheckte Public Key
ist leer; der Release-Workflow kann ihn beim Build ergänzen. Damit ist weder
„Updater fehlt vollständig“ noch „Updates funktionieren in verteilten Apps“ belegt.

**Ausbau:** Signierte Update-Kette für macOS und Windows praktisch nachweisen;
Update-Suche beim Start und periodisch konfigurierbar machen; verfügbare Version,
Release Notes, Fortschritt, Fehler und Wiederholen zeigen. Installation und
Neustart so koordinieren, dass ungespeicherte Entwürfe und laufende Arbeit nicht
verloren gehen. Keine erzwungene Unterbrechung einer Sitzung.

App, Sidecars und Python-Engine brauchen einen zusammenpassenden Versions- und
Migrationsvertrag. Update-Signatur und OS-Codesign/Notarisierung sind verschiedene
Prüfketten. Schlüsselrotation, Channels (intern/stabil als Vorschlag), Downgrade-
Politik und Wiederherstellung bei Fehlschlag vor Produktivbetrieb festlegen.
Tauri beschreibt die signierten Artefakte und Plattformformate in seiner
[Updater-Dokumentation](https://v2.tauri.app/plugin/updater/).

**Abnahme:** Installierte Version N → N+1 auf beiden Zielplattformen; ungültige
Signatur, Offline-Fall, Abbruch und laufende Sitzung testen. Keine Tags oder
Releases allein aufgrund dieses Playbooks auslösen.

### V1-03 — Integrationen: itsdcloud zuerst, lokal und bidirektional

**Gewünscht:** UI-Anbindung und MCP-Zugang zu
`/Users/mhennemeyer/WorkLocal/itsdcloud`. Projektgedächtnis steht dem gestarteten
Agenten automatisch zur Verfügung. Umgekehrt lassen sich z. B. Entwicklungsstand,
Entscheidungen und offene Punkte eines Features zurückschreiben. Später weitere
Adapter, insbesondere iKanban als Kandidat.

**Lokaler Codebefund vom 2026-09-10:** Der Ordner enthält die aktuellen Repos
`app` (Data-Plane), `portal` (Control-Plane) und `infra` sowie den früheren
`monorepo`-Baum. Einstieg für Projektwissen ist `app/backend`, nicht pauschal
der alte Monorepo. Laut App-README läuft die lokale Chat-API auf Port 8000.
Keine laufende Instanz, Anmeldung oder Verbindung wurde hier vorausgesetzt.

Vorhandene Verträge in `app/backend/app/routers/projects.py`:

- `GET /api/projects`: Projekte des angemeldeten Mitglieds.
- `GET /api/projects/{project_id}/memory`: `memory_md`, `memory_updated_at`;
  Mitgliedschaft ist Voraussetzung. Das Gedächtnis aggregiert `Chat.memory_md`.
- `POST /api/projects/{project_id}/memory/refresh`: erneute Extraktion aus Chats,
  mit Cooldown und möglichen Modellkosten — **kein** Schreibendpunkt für externe Fakten.
- Private Chat-Beiträge werden derzeit unter einer neutralen Überschrift
  mitaggregiert. Titel zu entfernen ist keine generelle Freigabe für jedes
  externe System; Exportumfang und Berechtigungen müssen ausdrücklich geklärt werden.

itsdcloud kann seinerseits externe MCP-Server als Projektintegration konsumieren.
Das ist die **andere Richtung**, noch kein veröffentlichter Memory-MCP für Speccify.

**Vorgeschlagener Schnitt:**

1. Lokalen Endpoint konfigurieren, anmelden und Speccify-Projekt explizit einer
   itsdcloud-Projekt-ID zuordnen. UI zeigt Verbindung, Rechte, letzte Aktualisierung
   und den tatsächlich freigegebenen Kontext; keine hartcodierten Benutzerpfade.
2. Gemeinsamer Integrationsadapter für UI und MCP: Projektliste, begrenztes
   Memory-Lesen/Suchen, Aktualität und Fehlerzustände. Ressourcen/Tools allein
   garantieren keinen Kontextabruf: Host-Startvertrag muss das initiale Laden
   anweisen oder den Kontext gezielt übergeben und dessen Bereitstellung sichtbar machen.
3. Automatisch lesen bei Auftragsstart bzw. relevantem Projektwechsel, nach
   konfiguriertem Budget/TTL; kein ungefragtes kostenpflichtiges `refresh`.
   Ausfall zeigt „offline/veraltet“, statt leeres Wissen als aktuell auszugeben.
4. Eigene Spec im itsdcloud-Repo für einen strukturierten Rückkanal: Feature-/Spec-ID,
   Repo/Branch/Commit-Bezug, Status, überprüfte Ergebnisse, offene Punkte,
   Revision und Idempotency-Key. Ein autorisierter Auftrag darf diesen Kanal
   im eingerichteten Umfang nutzen; kein pauschaler Datenbankzugriff.
5. Externe Entwicklungsnotizen als dauerhaftes, getrenntes Wissensobjekt führen,
   nicht durch Überschreiben einer Chat-Zusammenfassung. Aggregation, Korrektur,
   Konflikte und Löschung explizit regeln. Retries dürfen keine Dubletten erzeugen.

Lokale Anbindung bedeutet zunächst Loopback und keine gehostete Integrations-
Zwischenstelle. Das Betriebsmodell des gewählten Agenten/Modells ist davon
unabhängig. Tokens gehören in sicheren lokalen Speicher, nicht ins Repo.
Memory ist Datenkontext, keine Autorität für darin enthaltene Anweisungen.
Cross-Project-Leaks, ungewollte Pfad-/Quellcodeübertragung und private Inhalte
werden gezielt getestet. Bei Streamable HTTP sind außerdem Handshake,
Session-Neuaufbau, JSON/SSE-Antworten, Timeouts und Origin-Prüfung Vertragsbestandteile.

**Abnahme:** In einem lokalen Testprojekt bekommt ein neuer Agent-Auftrag ohne
Copy/Paste das richtige freigegebene Gedächtnis. Ein erlaubtes Feature-Update
erscheint nach bestätigtem Schreiben in itsdcloud und überlebt erneute
Chat-Extraktion. Offline, falsche Projektzuordnung, fehlende Rechte und doppelte
Schreibanforderung haben überprüfte Ergebnisse. In diesem Dokumentationsauftrag
werden weder itsdcloud-Dateien geändert noch Dienste gestartet.

### V1-04 — IDE-Fähigkeiten und Git ausbauen

**Nutzerfindings vom 2026-09-10:** Die vorhandenen Funktionen sollen deutlich
auffindbarer und wie ein zusammenhängender IDE-Arbeitsbereich wirken. Das
[UI-Playbook](ui-gestaltung.md) hält das laufend verfeinerte Farbkonzept fest.

- **Specs:** Archiv ist ein Rest des alten Workflows und entfällt als eigener
  Bedien-/Abschlussschritt. Vorhandene Specs/History nicht löschen; Altbestand
  weiterhin auffindbar halten. Alle Specs als einzelne Einträge links, mit
  gemeinsamer Auswahl in Board und Inspektor. Später nach Projekt sortieren,
  gruppieren und filtern. [Spec 020](../specs/020-spec-navigation/SPEC.md).
- **Git:** sichtbarer Commit-Composer und leicht erreichbare Branch-Auswahl;
  Branches wechseln und verwalten, Zustände/Fehler verständlich präsentieren.
  Umsetzung 021: Betreff/Body und projektgebundener Neustart-Entwurf im Hauptbereich,
  Index-Vorschau auch ohne Navigator. Lokale Branches suchen, bestätigt wechseln,
  anlegen/umbenennen/sicher löschen; Remote-/Tracking-/Worktree-Anzeige.
  Kein implizites Alles-stagen, Force-Delete oder automatischer Stash.
  [Spec 021](../specs/021-git-arbeitsbereich/SPEC.md).
- **Dateien:** Ordner zusätzlich zum Aufklappen auswählen können; unterschiedliche
  Dateityp-Symbole/Farben. Dateien und Ordner werden Aktionsziele für Kontextmenüs;
  später Move und weitere Refactorings mit Vorschau und klaren Sicherheitsgrenzen.
  Physisches Verschieben nicht als automatische Import-/Referenzanpassung ausgeben.
  [Spec 022](../specs/022-dateiauswahl-und-refactoring/SPEC.md).
- **Farbe:** ersten begrenzten Farbschnitt direkt umsetzen, anschließend anhand
  echter Nutzung verfeinern. Semantische Akzente, ruhige Flächen, Hell/Dunkel,
  keine allein farbliche Informationsvermittlung. [Spec 019](../specs/019-farbkonzept/SPEC.md).

019–021 sind durch den Fortsetzungsauftrag umgesetzt (Abnahmen offen);
022 bleibt konkretisierte Folgearbeit. Projektsortierung
setzt die Identitäten aus 015/016 voraus, kein zweites Multi-Repo-Modell erfinden.

**Bestand:** Editor mit mehreren Dateien, Entwürfen, Suche, Dateiverwaltung,
Git-Diffs, Hunk-Staging, Commits, Branches, Historie und Blame. Spec 002 enthält
noch Abnahmeaufgaben; das ist kein Auftrag, einen Editor von null zu bauen.

**Nächste Richtung:** Verlässlichkeit der Entwürfe/externer Dateiänderungen;
projektübergreifende Suche und Navigation; sprachbezogene Diagnosen und
Go-to-definition/Referenzen als mögliche LSP-Ausbaustufe. Git erhält klare
Repo-/Worktree-Auswahl, Konfliktansicht und sichere Merge-/Rebase-Abläufe,
Remote-/Upstream-Transparenz sowie später PR-/Review-Verknüpfung zum Spec-Board.
Debugger und vollständiger IDE-Ersatz sind noch kein zugesagter Umfang.

**Abnahme zuerst:** Zwei Repos mit offenen Entwürfen, externer Änderung und
Git-Konflikt; nichts wird still überschrieben oder im falschen Index gestagt.
Weitere IDE-Funktionen jeweils als eigenen vertikalen Schnitt spezifizieren.

### V1-05 — Feedback im Produkt und wiederverwendbare API

**Gewünscht:** Feedback-Tab mit sichtbarem Feedback anderer Nutzer, Suche und
Duplikatvermeidung. Zusätzlich Rechtsklick → Kontext-Menü → Feedback; Kontext
wird mit dem Eintrag gespeichert. Wiederverwendbar in anderen interaktiven Produkten.

**Produktfluss:** Liste suchen/filtern → vorhandenen Eintrag unterstützen oder
kommentieren → sonst neuen erstellen → Fortschritt/Antwort sehen. Kontextaktion
öffnet denselben Composer mit vorausgefülltem Bezug. Öffentliche und teaminterne
Einträge strikt trennen; „von anderen“ heißt nur innerhalb erlaubter Sichtbarkeit.

Vorgeschlagener gemeinsamer Vertrag:

- Versionierte API mit `product_id`, `tenant_id`, Feedback-ID, Titel, Beschreibung,
  Kategorie, Status, Duplikatbezug, Kommentaren und optionalen Stimmen/Anhängen.
- Kontext mit stabiler `surface_id`/`component_id`, App-Version, OS und optional
  Projekt-/Spec-/Action-Bezug; UI-Pfad ist ein lesbarer Snapshot, kein DOM-Dump.
- Vorschau vor Absenden; Screenshot, Logs, Dateiauswahl und Pfade nur gezielt
  hinzufügen und entfernen können. Kein automatischer Upload von Code, Terminal-
  Verlauf, Tokens, kompletten Projektpfaden oder fremdem Memory.
- Authentifizierung, Mandantentrennung, Rate-/Größenlimits, Moderation,
  Idempotenz, Datenexport und Löschung von Beginn an einplanen. Ein Desktop-Binary
  kann kein gemeinsames geheimes API-Passwort bewahren.
- Offline-Entwurf und verständlicher Sendezustand. Spec-Verknüpfung später möglich;
  Nutzermeldung und freigegebener Entwicklungsauftrag bleiben verschiedene Objekte.

**Hosting-Recherche, Preisstand 2026-09-10, USD:**

| Option | Einstieg und Nutzen | Abwägung |
|---|---|---|
| Cloudflare Workers + D1; Objektspeicher bei Anhängen | Free für Pilot; Workers Paid mindestens $5/Monat, 10 Mio. Requests/Monat inklusive. D1 enthält im Paid-Tarif 5 GB sowie erhebliche Read-/Write-Kontingente. | Kleine API kostengünstig; Auth, Moderation, Backups und Betriebsoberfläche sind trotzdem Arbeit. |
| Supabase | Free für Pilot; Pro ab $25/Monat, $10 Compute-Guthaben decken eine Micro-Instanz. Postgres plus Auth-/Storage-/Realtime-Bausteine. | Höherer Grundpreis, mehr fertige Infrastruktur; zusätzliche Projekte/Nutzung erhöhen Kosten. |
| Bestehende eigene Infrastruktur | Kleine API mit vorhandener Datenbank denkbar; keine belastbare Zusatzkostenangabe ohne Kapazitätsprüfung. | Gemeinsamer Betrieb, Backups, Updates und Ausfallradius; nicht automatisch kostenlos. |

Belege: [Workers-Preise](https://developers.cloudflare.com/workers/platform/pricing/),
[D1-Preise](https://developers.cloudflare.com/d1/platform/pricing/),
[Supabase-Preise](https://supabase.com/pricing).

**Empfehlung, noch keine Anbieterentscheidung:** Wiederverwendbaren API-Kern und
kleinen eingebetteten Feedback-Client bauen, zuerst nur für Speccify einsetzen.
Workers/D1 als günstigen Pilot prüfen; Supabase bevorzugen, falls vorhandene
Team-Authentifizierung und relationale Administration mehr Entwicklungszeit sparen.
Nicht vor der zweiten echten Nutzung einen vollständigen SaaS-Marktplatz bauen.

Ein kleiner interner Pilot kann innerhalb der freien Kontingente liegen; für
Workers Paid ist $5 lediglich die Basis, kein pauschaler Gesamtpreis. Anhänge,
Auth/Mail, Domain, Backups, Observability und Mehrverbrauch separat kalkulieren.
Vor Betrieb Datenregion/Verträge, Aufbewahrung, Berechtigungskonzept, Kostenlimits
und verantwortliche Betreuung festlegen. Noch nichts buchen oder deployen.

**Abnahme:** Zwei Nutzer sehen berechtigtes Feedback, finden einen bestehenden
Eintrag statt eines Duplikats und reichen kontextbezogenes Feedback mit kontrollierbarer
Vorschau ein. Ein zweites Testprodukt nutzt denselben API-Vertrag, sieht aber
keine privaten Speccify-Einträge. Offline-/Retry- und Missbrauchsfälle prüfen.

### V1-06 — Ad-hoc-UIs für Aktionen und Profiling

**Gewünscht:** Aktionen können passende Oberflächen öffnen, z. B. Profiling
mit Echtzeitdiagrammen, Messwerten und Steuerung.

**Bestand:** Aktionen haben Eingabeformulare, laufende Ausgabe, Stop und einfache
JSON-Zeilen-Diagramme (`kind: chart`, Serien als Linie/Balken). `toolui:`-
Kommandos sind als „App-Panel — folgt“ markiert, kein fertiges Panel-System.
Spec 018 ergänzt Ausgabetabs neben dem Inspektor: Start öffnet automatisch die
rechte Seitenleiste, ein Tab je Aktion mit Status und Stop. Ausgabe bleibt im
Fensterspeicher bis zum Schließen, erneuter Lauf ersetzt sie; maximal 2000 Elemente.
Kein historisches Laufarchiv oder Ersatz für das geplante Panel-Schema. Der
Bereitstellungs-/Abnahmestand steht in Spec 018.

**Vorschlag:** Versioniertes deklaratives Panel-Schema mit einem begrenzten
Komponentenkatalog (Zeitreihe, Kennzahl, Tabelle, Auswahl, Start/Stop). Daten über
versionierte Ereignisse mit Run-ID, Projekt/Repo, Sequenz, Zeitstempel, Einheit
und Update-/Append-Semantik; Limits, Pufferung, Downsampling und Abbruch regeln.
Keine beliebigen nachgeladenen Skripte mit Tauri-Rechten als Standard.

**Abnahme:** Ein Profiling-Fixture aktualisiert dieselbe Zeitreihe live, lässt
sich stoppen und exportieren; hohe Ereignisrate, kaputte Daten, Prozessende und
Panelwechsel blockieren weder UI noch Prozessverwaltung. Ausgaben bleiben diagnostizierbar.

### V1-07 — Tutorials neu aufbauen

**Jetzt:** 4Notice komplett gegen Specs/Playbooks und die aktuelle App neu
durchlaufen. Vorhandene Kapitel beschreiben noch `.agent/plans`, `.agent/board`,
Tickets und „In Progress“. Das ist eine Workflow-Neufassung, kein Wortersetzungslauf.

Neuer Lernbogen: Voraussetzungen → leeres Projekt → Playbook/Vision → erste
abnehmbare Spec → Agent-Terminal → Skills importieren/expandieren → Tools prüfen
→ Umsetzung und Git → Fragen/Abnahme → Skill generalisieren/exportieren → Release.
macOS/iOS-spezifische Store-Schritte klar von der allgemeinen Speccify-Methode
trennen; notwendige Accounts und Kosten vor dem jeweiligen Abschnitt nennen.

DE und EN inhaltlich synchronisieren; App-Hilfe, Website, Beispiele und Screenshots
gegen dieselbe Version prüfen. Historische Beobachtungen nicht als aktuellen
Bedienpfad darstellen; unvollständige Kapitel kennzeichnen, alte URLs umleiten.

**Später:** Ein umfangreiches Beispiel mit Server/Client, mehreren Repos,
Integrationstests, Team-Board, Profiling und gemeinsamem Skill-Target.
.NET oder Java Spring bleiben Optionen; Auswahl erst nach Lernziel und
Teambedarf, nicht beides gleichzeitig versprechen.

**Abnahme:** Unbeteiligter Kollege schafft den dokumentierten Durchlauf mit
frischem Checkout. Jeder Schritt hat erwartetes Ergebnis und Wiederaufnahmeweg.

### V1-08 — Mehrere Skill-Repos, Sources und Targets

**Gewünscht:** Mehrere Bibliotheken gleichzeitig anbinden. **Jedes Target ist
auch Source; nicht jede Source ist Target.** Ein Target ist das Team- oder
öffentliche Repo, in das lokale Skills nach Generalisierung zurückgegeben werden.

**Bestand:** Mehrere globale/projekteigene Git-/Ordnerquellen, Browse, Import,
Expand und Export existieren. Der Exportdialog nimmt derzeit jede Quelle mit
lokalem Checkout als mögliches Ziel; Absicht und Schreibfähigkeit sind nicht getrennt.

**Ausbau:** Explizite Rolle `source` oder `source+target`; Team/öffentlich als
Sichtbarkeit, nicht als automatisch aus einer URL abgeleitete Eigenschaft.
Lesen, lokal exportieren und upstream veröffentlichen haben unterschiedliche
Voraussetzungen. Ein beschreibbarer Cache beweist kein Push-Recht.

Import zeigt Herkunft, Version/Ref, Projektbezug und Namenskonflikte. Export
zeigt Target, Branch, Änderungen und Generalisierungsbefunde. `In this project`
entfernen reicht nicht: Verträge, Referenzimplementierungen, Fixtures, sensible
Werte und implizite Annahmen prüfen. Anschließend Roundtrip in sauberem Projekt.
PR/Review vor Veröffentlichung als Teamoption; keine automatische Veröffentlichung
privaten Wissens. Upstream-Updates erhalten projektspezifische Ergänzungen.

**Abnahme:** Read-only Source A und Target B parallel nutzen; A ist nicht als
Publikationsziel auswählbar. Generalisierter Skill aus B lässt sich in Projekt C
ohne Wissen aus Projekt A expandieren und prüfen. Spec 004 dabei fortführen,
nicht deren bereits vorhandene Quellenverwaltung erneut planen.

### V1-09 — Team-Board trotz Feature-Branches

**Problem:** Specs müssen allen über Backlog/Doing/Done sichtbar bleiben, während
Code und zum Code passende Tool-/Skill-Stände in verschiedenen Branches liegen.
Ein Branchwechsel darf weder Arbeit verstecken noch irrtümlich den Teamstatus ändern.

**Nicht als Regel übernehmen:** „Alles aus `.agent` immer vom Feature-Branch nach
`main` schieben.“ Dort liegen auch Tools, Skills, Konfiguration und Anweisungen,
deren Stand zur unfertigen Implementierung gehört. Statussichtbarkeit ist keine
Freigabe für deren Integration. Selektives Kopieren derselben Spec zwischen
Branches ohne eindeutige Wahrheit produziert ebenfalls widersprüchliche Zustände.

| Modell | Vorteil | Schwierigkeit |
|---|---|---|
| Specs bleiben in Code-Branches; Board aggregiert Git-Refs | Wenig neue Infrastruktur, branchgenaue Dokumente | Nur gepushte/fetchbare Arbeit für andere sichtbar; Dubletten, Statusautorität und parallele Bearbeitung müssen aufgelöst werden |
| Gemeinsames Spec-Register in separatem Metadaten-Repo | Unabhängig vom Code-Branch, offline Git-fähig, passt zum Multi-Repo-Modell | Eigener Sync-/Konfliktvertrag und Bindung an Code-Revisionen nötig |
| Zentraler Board-Dienst | Rechte, gleichzeitiges Bearbeiten und Live-Status gut modellierbar | Auth/Betrieb/Offline-Sync und neue dauerhafte Serverabhängigkeit |

**Entschieden am 2026-09-10 (D-TEAM-01):** Separates Metadaten-Repo als gemeinsames
Spec-Register erproben. Pilot: [Spec 016](../specs/016-gemeinsames-spec-register/SPEC.md).
Die oben genannten Alternativen bleiben als Abwägung dokumentiert, sind aber
nicht der gewählte Pilot. Kein dauerndes Umschalten des Code-Checkouts. Git unterstützt
mehrere Arbeitsbäume pro Repo; die Board-Semantik ist unser zusätzlicher Vertrag,
nicht etwas, das Git automatisch löst.
([Git-Worktree-Dokumentation](https://git-scm.com/docs/git-worktree))

Konkreter vorgeschlagener Ablauf:

1. Spec mit stabiler ID im gemeinsamen Register anlegen und synchronisieren;
   Nummer ist Anzeige, keine global kollisionsfreie Identität.
2. Übernahme/Doing mit Person, Projekt und betroffenen Repos sichtbar machen.
   Zwei gleichzeitige Übernahmen über erwartete Revision erkennen, nicht still überbügeln.
3. Feature-Branches/Worktrees arbeiten gegen diese ID und eine nachvollziehbare
   Spec-Revision. Lokale Entwürfe und ungesendete Statusänderungen bleiben sichtbar markiert.
4. Fortschritt/Fragen über normale Metadaten-Commits synchronisieren; konkurrierende
   Änderungen per Fetch/Rebase/Review auflösen. Append-only History allein macht
   die Dateien noch nicht konfliktfrei. Kein automatischer Force-Push.
5. Fachliche Abnahme und Integration auseinanderhalten: `ready/needs_human`
   können Review signalisieren; `Done` verlangt die in der Spec definierte Abnahme
   und erforderliche integrierte Code-Revisionen. PR offen bedeutet nicht Done.
6. Zum Code-Release den maßgeblichen Spec-Stand referenzieren oder als ausdrücklich
   nicht editierbaren Snapshot pinnen. Historische Anforderungen müssen reproduzierbar bleiben.

Gemeinsame Vision/Playbooks können im Register leben. Codegebundene Skills,
Tools und Anweisungen verbleiben standardmäßig im Code-Repo. Ein verknüpftes
Register ist eine Referenz, keine zweite frei editierbare Kopie derselben Specs.
Projekte ohne Team-Anbindung behalten ihr lokales `.agent/specs` als Wahrheit.

**Noch offen für den realen Team-Pilot:** konkretes Register-Repo und Zugriffsrechte,
Übernahme-/Review-Regeln, Offline-Fenster und benötigte Aktualität mit zwei
Teammitgliedern am konkreten Beispiel festlegen. Lokale Fixtures benötigen diese
externen Angaben noch nicht; keine bestehenden Specs automatisch migrieren.
**Abnahme:** Zwei Checkouts, zwei Feature-Branches, eine gemeinsame Spec: Fortschritt
sichtbar ohne Code-Merge; parallele Änderung erzeugt Konflikthinweis; Offline und
abgebrochener Branch lassen weder Arbeit verschwinden noch den Status fälschlich schließen.

## Vision 2: nach breiter interner Nutzung

### V2-01 — Fremde Spec-Workflows ohne Zwangsmigration

Ordner öffnen, die vollständig OpenSpec oder GitHub Spec Kit folgen. Speccify
soll deren Artefakte verstehen und darstellen, ohne erst `.agent` aufzuzwingen.
OpenSpec trennt bestehende Spezifikationen und Änderungen; Spec Kit hat eigene
Projektstruktur, Vorlagen und Arbeitskommandos. Diese Semantik darf nicht allein
aus ähnlichen Dateinamen in Speccify-Stationen umgedeutet werden.
([OpenSpec](https://github.com/Fission-AI/OpenSpec),
[GitHub Spec Kit](https://github.com/github/spec-kit))

**Vorschlag:** Versionierte Workflow-Adapter mit Erkennung, Artefaktliste,
Beziehungen, Statusabbildung, Fähigkeiten und erlaubten Schreiboperationen.
Zuerst read-only mit Herkunftskennzeichnung; später originale Werkzeuge oder
formatspezifische Mutationen. Unbekannte Zustände sichtbar erhalten. Gemischte
Workspaces und kollidierende Erkennung brauchen eine explizite Auswahl.

**Abnahme:** Je ein unverändertes Referenzprojekt pro System öffnen; Specs,
Tasks und Zusammenhänge korrekt lesen, ohne Setup-Dateien anzulegen. Schreib-
Roundtrip erst mit eigenen Fixtures und versioniertem Kompatibilitätsnachweis.

### V2-02 — `.skill` und allgemeine Skill-Interoperabilität

**Rechercheergebnis:** `.skill` ist bei Anthropics Packaging-Skript ein ZIP-Archiv
mit anderer Endung, nicht ein grundsätzlich anderes Anweisungsformat. Das offene
Agent-Skills-Format beschreibt einen Ordner mit `SKILL.md`, Frontmatter und
optionalen Ressourcen. Die Dateiendung allein beweist also weder Konformität
noch Vertrauenswürdigkeit.
([Anthropic-Paketierung](https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/package_skill.py),
[Agent-Skills-Spezifikation](https://agentskills.io/specification))

**Vorschlag:** Kanonisch bleibt der Skill-Ordner. Importadapter für Verzeichnis,
Git, `.zip` und `.skill`; Exportprofile nach tatsächlichem Zielsystem. Metadaten,
Ressourcen, Lizenz und Erweiterungen erhalten; Speccify-Tool-Verträge nicht als
universell unterstützte Fähigkeit fremder Hosts ausgeben.

Archive vor dem Expand prüfen: kein Zip-Slip/Pfad außerhalb des Ziels, keine
Symlink-Flucht, Größen-/Dateianzahllimit, gültiges Root-Layout, keine automatische
Skriptausführung. Mehrdeutige Pakete zeigen einen Fehler oder eine Vorschau.

**Abnahme:** Referenzpaket importieren, lesen, zielgerecht exportieren und erneut
importieren, ohne Inhalte zu verlieren; beschädigte oder ausbrechende Archive
werden abgewiesen. Kein neues konkurrierendes Format erfinden, solange ein
Adapter genügt. Formatsupport vor Umsetzung erneut gegen Primärquellen prüfen.

## Offene Produktentscheidungen

### Was vor welchem Schritt entschieden werden muss

**Der Start der Weiterentwicklung ist nicht blockiert.** Lokalen Betrieb,
Startdiagnose und bestehende Konsistenzbefunde können wir unabhängig davon
bearbeiten. Priorität aus dem Auftrag vom 2026-09-10: App möglichst verfügbar
halten, früh selbst nutzen, Feedback sammeln und kontinuierlich abnehmen.

| Wann | Benötigte Entscheidung | Entscheidung / verbleibender Vorschlag |
|---|---|---|
| Vor dem Multi-Repo-Datenmodell | Was bildet ein Projekt, wie werden mehrere Repos gruppiert? | **bestätigt 2026-09-10:** erkannte Repos zunächst separat, fachliche Gruppierung anpassbar (D-MR-01) |
| Vor dem Team-Sync | Welche gemeinsame Quelle ist für Specs verbindlich? | **bestätigt 2026-09-10:** separates Spec-Repo als interner Pilot (D-TEAM-01); konkretes Remote/Rechte später |
| Vor itsdcloud-Datenzugriff | konkrete Instanz/Projektbindung und freigegebenes Wissen, besonders private Chat-Beiträge | lokal, zunächst nur lesend, ausgewähltes Projekt |
| Vor dem Memory-Rückkanal | welche Entwicklungsnotizen dürfen geschrieben werden, wer darf korrigieren? | getrennte Feature-Notizen, begrenzte Rechte, kein Überschreiben des Chat-Memory |
| Vor Feedback-Betrieb | intern/öffentlich, Identität, Betreiber und Hostingbudget | intern beginnen, wiederverwendbaren API-Kern erst lokal testen |
| Vor automatischer Verteilung | Channels, Signaturschlüssel, Neustartpolitik | interne Builds, Update anzeigen, laufende Arbeit nicht unterbrechen |

Die Technologie des zweiten Tutorials und Details der Zukunftsadapter können
warten. Produktentscheidungen nicht aus vorgeschlagenen Defaults als bereits
erteilte Zustimmung ableiten.

Die Wünsche sind erfasst; diese Entscheidungen sind noch nicht freigegeben:

- Detaildarstellung des gemeinsamen Workspace-Kontexts; die frei anpassbare
  Repo-Gruppierung selbst ist mit D-MR-01 entschieden.
- Konkretes Register-Repo, Rechte und Definition von Übernahme/Abnahme/Integration;
  die gemeinsame Quelle als separates Spec-Repo ist mit D-TEAM-01 entschieden.
- itsdcloud-Authentifizierung für externe lokale Clients, Umfang exportierbaren
  Wissens und dauerhafter Schreibvertrag; iKanban-Vertrag erst danach untersuchen.
- Update-Channels und Installations-/Neustartpolitik.
- Feedback-Sichtbarkeit, Anmeldung, Hosting und Betriebsverantwortung.
- Reihenfolge der vertieften IDE-Funktionen; .NET oder Spring für Tutorial zwei.

Bestehende offene Arbeit aus Specs 001–005 bleibt erhalten. Insbesondere offene
Abnahmen, Wissens-/Tool-Roundtrips und Website-Lokalisierung werden durch diese
Vision nicht automatisch abgeschlossen oder verworfen.

## Dokumentationsprüfung und Änderungsnotiz

2026-09-10: D-MR-01 und D-TEAM-01 durch ausdrückliche Bestätigung beschlossen;
Specs 015/016 als getrennte Backlog-Schnitte angelegt. Keine bestehende Spec
migriert, kein externes Repo angelegt und kein laufender App-Prozess neu gestartet.

2026-09-10: Produktvision V1/V2 aufgenommen; bestehende Entwicklungsanleitung
beibehalten, separates Bestands-/UI-Playbook eingeführt. Codebefunde zu Updater,
Quellen, Aktionsdiagrammen und lokaler itsdcloud-API gegen „komplett neu“ geprüft.
Skill-Suche nach `playbook` ohne Treffer; bestehende Speccify-Konventionen verwendet.
Die Transport-Checkliste aus `mcp-client-streamable-http` beeinflusst den geplanten
Integrationsvertrag; sie ist hier kein ausgeführter Verbindungstest. Keine
Tool-Implementierung oder Plattformprüfung wurde durch diese Dokumentation abgenommen.

## Arbeitsweise: Speccify weiterentwickeln

### Laufende Nutzung und Abnahme

Auftrag vom 2026-09-10; Umsetzung in
[Spec 013](../specs/013-lokale-app-und-startdiagnose/SPEC.md).

```sh
./scripts/dev.sh --status --ui-port=18768
./scripts/dev.sh --open --ui-port=18768
# Neuer lokaler Build, nachdem Arbeit gesichert und die App bewusst beendet wurde:
./scripts/dev.sh --app --prepared --ui-port=18768
```

Lokale neu gebaute Apps können erneut die macOS-Freigabe für den Ordner
Schreibtisch verlangen (beobachtet bei Spec 008). Ein erreichbarer MCP-Port
beweist dann noch keine bedienbare Oberfläche. Dialog vom Nutzer bestätigen
lassen und anschließend Projektfenster/Terminal-Wiederaufnahme prüfen; keine
Systemfreigabe umgehen oder einen erfolgreichen Neustart nur aus dem Port ableiten.

Die gebündelte App braucht keinen Entwicklungsserver und bleibt während
Codeänderungen/Tests offen. `--prepared` nur bei bereits eingerichteten,
bekannt passenden Deps/Sidecars/Payload verwenden; sonst zuerst `--no-start`.
Seit der Präzisierung vom 2026-09-10 sind Neustarts für Updates ausdrücklich
erlaubt und erwünscht: vorher kurz ankündigen, Entwürfe/laufende Arbeit beachten,
anschließend die App wieder starten und Wiederaufnahme prüfen. Dafür nicht jedes
Mal neue Erlaubnis verlangen. Ein zeitweiliges „jetzt nicht neu starten“ geht vor;
die temporäre Sperre für die Kollegen-Demo aus Spec 017 ist inzwischen aufgehoben.
Der anschließende Fortsetzungsauftrag erlaubt ausdrücklich beliebig viele nötige
Update-Neustarts während der Abwesenheit; App danach weiter geöffnet halten.
Bei Abnahmen den tatsächlich gestarteten Build benennen; gespeicherte Specs und
Playbooks sind live lesbar, Programmänderungen erst nach neuem Build/Start.

Vor und nach Entwicklungsarbeit Prozess/Endpoint prüfen. Nicht aus einem belegten
Port eine Speccify-Instanz ableiten; am Bestandsdatum gehört 8768 Lima, daher
explizit 18768 für die lokale App. `--open` ist Wiederöffnen, kein dauerhafter
Autostart-Dienst und kein automatischer Portwechsel einer laufenden App.

Bei Änderungen an `crates/mcp-core` oder den Rust-MCPs vor `--prepared` die
Sidecars mit `scripts/build_sidecars.sh --debug` neu bauen. Spec 014 definiert
deren gemeinsame lokale HTTP-Grenze: keine Browser-Origins freigegeben,
Host/Port fest geprüft, POST nur JSON und höchstens 1 MiB Anfragekörper.
Details und Restgrenzen: [HTTP-Vertrag](../../docs/exec-mcp-contract.md).
Neue Browserintegrationen dürfen keine pauschale localhost-/CORS-Ausnahme einführen.

Bis zum Feedback-Panel: Rückmeldung mit Bereich, Ist/Soll, reproduzierbaren
Schritten und Buildstand in der betroffenen Spec unter Questions/Verification
festhalten; unabhängige Fehler als eigene Spec. Keine privaten Logs pauschal
anhängen. Menschliche Abnahme hält eine vorbereitete Spec bis zur Bestätigung
in Doing; grüner Handshake oder Build setzt sie nicht automatisch auf Done.

Diese Anleitung gilt für wiederkehrende Entwicklungsarbeit am Speccify-Repo.
Die einzelnen Aufträge stehen in `.agent/specs/`; dieses Playbook bleibt als
Arbeitsweise bestehen. Projektvereinbarungen in `.agent/agent.md` und der
konkrete Auftrag gelten vor allgemeinen Workflow-Vorlagen.

## Ziel

Eine Person kann ein Projekt öffnen, einen Auftrag an ihren gewählten Agenten
geben und dessen Arbeit an Specs, Dateien, Skills und Werkzeugen nachvollziehen.
Der Ablauf funktioniert auch mit einem frischen Checkout und nach einem
App-Neustart. Speccify verwaltet Dateien und stellt Arbeitsmittel bereit;
das gewählte Agent-Werkzeug führt den Auftrag aus.

## 1. Mit dem tatsächlichen Stand beginnen

Lies `.agent/agent.md`, die benannte Spec und deren Abhängigkeiten. Die
[Bestandsaufnahme vom 10. September 2026](../specs/006-bestandsaufnahme-agent-terminal/SPEC.md)
ist der Ausgangspunkt dieser Ausbauphase. Prüfe ihre Befunde erneut, sobald
betroffener Code geändert wurde. Alte Status- und Resume-Dateien sind Historie.

Prüfe `git status --short`. Ordne vorhandene Änderungen zu und erhalte sie.
Unterscheide beim Ergebnis immer Codebefund, bestandenen Test und Beobachtung
in der echten App. Ein Mock oder ein offener Port belegt keine App-Abnahme.

**Prüfung:** Der aktuelle Auftrag, seine Grenzen und der überprüfte Commit sind
benannt. Bereits gelieferte Funktionalität wird nicht erneut geplant.

## 2. Arbeitsumgebung feststellen

Im Projektverzeichnis:

```sh
command -v speccify
speccify --help
uv run --frozen --no-sync speccify --help
uv run --frozen --no-sync speccify verify --offline
```

Die beiden Hilfe-Ausgaben müssen nicht dieselbe Installation verwenden.
Am 10. September kannte die globale CLI `expand`, `export`, `link` und `tool`
noch nicht. Für Entwicklung in diesem Repo deshalb die Workspace-CLI über
`uv run` verwenden. Fehlt die vorbereitete Umgebung, gilt die Einrichtung
aus README und `scripts/dev.sh`; ein Prüfaufruf soll keine Installation tarnen.

Prüfe zusätzlich die Verweise von `AGENTS.md`/`CLAUDE.md` auf `.agent/agent.md`
und von `.agents/skills`/`.claude/skills` auf `.agent/skills`. Die Existenz eines
Links allein beweist weder ein erreichbares noch das richtige Ziel.

**Prüfung:** Projektwurzel, tatsächlich verwendete CLI und benötigte Befehle
sind bekannt. Meldet `verify` fehlende Tools, ist der Lockfile-Stand trotzdem
konsistent möglich; die Ausführbarkeit ist damit noch nicht nachgewiesen.

## 3. Eine abnehmbare Spec wählen

Ein benannter Auftrag bestimmt die Spec. Sonst gilt die vereinbarte
Backlog-Reihenfolge. Der Auftrag, eine Spec umzusetzen, ist die Freigabe für
`Backlog → Doing`; innerhalb dieses Auftrags sind normale Umsetzungsschritte
abgedeckt. Ein reiner Überblicks- oder Planungsauftrag startet keine
Implementierungsspec. Pro Sitzung wird eine Spec bearbeitet; bestehende
`Doing`-Einträge anderer Arbeit werden nicht automatisch verschoben.

Jede neue Spec enthält `Why`, `What`, `Acceptance`, `Decisions`, `Tasks`,
`Verification` und `Questions`. Wähle die nächste freie Nummer auch unter
Berücksichtigung des Archivs. Beschreibe Akzeptanz als beobachtbares Verhalten:
Auslöser, Ergebnis und Fehlerfall. Halte Aufgaben ausschließlich unter
`## Tasks`. Seit Spec 008 verwenden Board-Zähler, Aufgabenliste und Klick dieselbe
native Markdown-Erkennung: Tasklisten im gesamten Body zählen, Codeblöcke nicht.
Bei veraltetem angezeigtem Body verweigert die App den Klick und lädt neu.

Workflow-Einrichtung (Policy v5): ausdrückliche Projekt-/Hostregeln haben Vorrang,
auch bei Commit/Push und Herkunftsangaben. Das Setup aktualisiert ausschließlich
bekannte unveränderte ältere Vorlagen. Angepasste Skills/Policy-Blöcke, unbekannte
neuere Versionen und beschädigte/falsche Links bleiben mit konkretem Befund
erhalten. `current` setzt passende Linkziele und Vorlagen voraus, nicht nur ihre
Existenz. Individuelle Anpassung ist kein Datenverlust und kein Auto-Reparaturauftrag.

**Prüfung:** Ein Review kann entscheiden, ob diese eine Arbeit fertig ist.
Abhängigkeiten und ausdrücklich ausgelassene Funktionen stehen in der Spec.

## 4. Am Arbeitsablauf entlang umsetzen

Prüfe vor dem Bauen widersprüchliche Anforderungen und versteckte Abhängigkeiten.
Benutze vorhandene Skills, wenn sie den konkreten Ablauf abdecken. Verträge
aus `TOOL.md` werden vor einer Tool-Implementierung vollständig gelesen.
Nutze vorhandene Core-Funktionen; CLI und MCP bleiben dünne Adapter. Native
Desktop-Funktionen erhalten einen eindeutigen Vertrag zwischen Rust und UI.

Ticke abgeschlossene Tasks, halte Entscheidungen und tatsächliche Ergebnisse
fest. Neue Aufgaben gehören in dieselbe Spec, solange sie für deren Akzeptanz
erforderlich sind. Andere Verbesserungen bekommen eine eigene Backlog-Spec.
Kündige Rust-Änderungen vorab an: `tauri dev` kann dadurch neu starten.

**Prüfung:** Jede Änderung lässt sich auf die Akzeptanz zurückführen. Daten,
Regeln und Status haben jeweils eine erkennbare Quelle der Wahrheit.

## 5. Gegen konkrete Fehler prüfen

Beginne mit den betroffenen vorhandenen Tests. Typische Prüfungen:

| Änderung | Prüfung |
|---|---|
| Core, CLI, MCP | `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` |
| Desktop-Frontend | `pnpm --filter speccify-desktop typecheck` und betroffener UI-Ablauf |
| Desktop-Rust | `cargo test -p speccify-desktop`, `cargo fmt --check` |
| Tool-Implementierung | `uv run speccify tool check <name>` und Prüfung des tatsächlichen Ergebnisses |
| Playbook oder Spec | Struktur, interne Links, eindeutige Nummern, Akzeptanz und Aufgaben prüfen |

Neue Tests müssen einen relevanten Fehler erkennen können. Tests, die nur
den Aufbau des Codes wiederholen, ersetzen keine Verhaltensprüfung.
Eine Sandbox-Sperre für lokale Testports ist getrennt von einem Produktfehler
zu dokumentieren; ein fehlgeschlagener Test wird nicht still übergangen.

Bei Terminal-Änderungen prüfe frischen Start, UTF-8-Ausgabe, mehrzeiliges
Einfügen, Ctrl-C, Ende des Prozesses und Neustart. Bei Workflow-Änderungen
prüfe vorhandene Projektanweisungen, eigene Skills, defekte Links und
zwischenzeitliche Dateiänderungen. Bei Skill-Prüfungen vergleiche CLI, MCP
und UI am selben Projektzustand.

**Prüfung:** Die Spec nennt Befehle, Resultate, ausgelassene Prüfungen und die
Fehlerfälle, die tatsächlich versucht wurden. Unbekannte Messwerte bleiben
unbekannt; Tokenzahlen werden nicht geschätzt oder erfunden.

## 6. In Speccify abnehmen und übergeben

Für Änderungen am Arbeitsablauf gehört ein Durchlauf im echten Projektfenster
zur Abnahme. Dazu ein entbehrliches Testprojekt verwenden. Die vollständige
Matrix steht in [Spec 012](../specs/012-agent-terminal-praxisabnahme/SPEC.md).
Ein Browser-Mock deckt Rendering ab, aber weder native PTYs noch Host-Login
oder die Auswahl der fortgesetzten Sitzung.

`Done` bedeutet: alle Aufgaben erledigt und Akzeptanz belegt. Wenn
`needs_human: true` gilt, bleibt die Spec mit `ready: true` in `Doing`, bis
die menschliche Abnahme erfolgt. Bei einer offenen Voraussetzung dokumentiere
den konkreten Rest und setze nicht vorschnell `ready`.

Historie wird angehängt und wahrt die geltenden Attributionsregeln. Für
Commits und Push gelten die ausdrücklichen Projektvereinbarungen; Release-Tags
und Veröffentlichungsentscheidungen bleiben gesonderte Aufträge.

**Prüfung:** Die nächste Sitzung findet Ergebnis, offene Punkte und den
nächsten freigegebenen Schritt in Dateien. Ein bereits erteilter Auftrag
muss nicht erneut bestätigt werden.
