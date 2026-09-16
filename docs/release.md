# Release: Speccify.app für macOS

> **Windows:** Der Job `release-windows` in `release.yml` baut auf demselben
> Tag einen x64-NSIS-Installer (`*-setup.exe`) plus MSI und hängt beide an
> dasselbe Draft-Release an. Ohne Azure-Secrets unsigniert — SmartScreen
> warnt beim ersten Start; mit den sechs `AZURE_*`-Secrets signiert der Job
> über Azure Trusted Signing (siehe Aktionsliste unten). Sidecars entstehen
> im Workflow selbst (pwsh, Release-Profil); das Engine-Payload-Skript läuft
> im Git-Bash des Runners.

Speccify wird **außerhalb des App Store** verteilt (Plan
[`r5-distribution`](../.agent/specs/archive/2026-08-04-r5-distribution/SPEC.md), D5): Download über
GitHub-Releases statt Store, ohne Sandbox — der Exec-MCP und der
Prozess-Supervisor starten beliebige CLI-Befehle, das ginge sandboxed nicht.

## Der normale Weg: ein Tag

Seit Spec 028: Läuft das Projekt mit gemeinsamem Spec-Register, den Commit des
Branch `specs` in den Release-Notizen nennen (`git -C .agent/specs rev-parse HEAD`),
damit der Anforderungsstand zum Code reproduzierbar bleibt.

`.github/workflows/release.yml` baut auf jedem `v*`-Tag: Sidecars,
Engine-Payload, `tauri build`, und legt einen **Entwurfs-Release** an. Der
letzte Blick auf das, was Nutzer bekommen, ist ein Mensch, der die
Release-Seite öffnet — nicht eine grüne Pipeline.

```bash
git tag v0.2.0 && git push origin v0.2.0
```

Updater-Signaturen sind für alle Release-Plattformen verpflichtend. Fehlende
Schlüssel oder unvollständige Update-Pakete lassen den Workflow fehlschlagen.
Apple-/Windows-Codesigning ist davon unabhängig konfiguriert.

Das lokale Skript unten bleibt für Tests und für den Fall, dass man ohne CI
ausliefern will.

## Signierung scharf schalten — die Aktionsliste

Die vier Plattform-Jobs und die abschließende Manifest-Prüfung sind verdrahtet.
Alle Secrets/Variablen entstehen **außerhalb des Repos** und werden mit
`gh secret set <NAME>` bzw. `gh variable set <NAME>` hinterlegt (oder im
GitHub-UI unter *Settings → Secrets and variables → Actions*). Kein Wert
gehört jemals in eine getrackte Datei.

### macOS (Gatekeeper): 4 Schritte

> **Stand 2026-09-01:** Schritt 1 und der Erzeugen-Teil von Schritt 2
> entfallen — das Developer-Konto existiert (Team `9MQUMBML8C`, dasselbe
> wie bei iKanban), und ein gültiges Zertifikat
> `Developer ID Application: Matthias Hennemeyer (9MQUMBML8C)` liegt
> bereits im Login-Keychain dieses Macs. Es bleibt: exportieren (2b),
> App-Passwort (3), optional Updater (4).

1. **Apple Developer Program** beitreten (99 $/Jahr,
   [developer.apple.com](https://developer.apple.com/programs/)).
2. **Developer-ID-Zertifikat** erzeugen (Portal → Certificates →
   *Developer ID Application*), in den Login-Keychain importieren, dann als
   `.p12` exportieren (Schlüsselbund → Zertifikat + privater Schlüssel →
   Exportieren, Passwort vergeben) und hinterlegen:

   ```bash
   base64 -i DeveloperID.p12 | gh secret set APPLE_CERTIFICATE
   gh secret set APPLE_CERTIFICATE_PASSWORD        # das Export-Passwort
   security find-identity -v -p codesigning        # → den vollen String:
   gh secret set APPLE_SIGNING_IDENTITY            # "Developer ID Application: Name (TEAMID)"
   ```

3. **Notarisierungs-Zugang**: auf [appleid.apple.com](https://appleid.apple.com)
   ein app-spezifisches Passwort erzeugen, dann:

   ```bash
   gh secret set APPLE_ID          # die Apple-ID-Mailadresse
   gh secret set APPLE_PASSWORD    # das app-spezifische Passwort
   gh secret set APPLE_TEAM_ID     # die TEAMID aus der Klammer der Identity
   ```

4. **Updater-Schlüssel** (seit Spec 050 eingerichtet; nicht neu erzeugen):

   ```bash
   # Nur zur erstmaligen Einrichtung, niemals einen bestehenden Schlüssel ersetzen:
   pnpm --filter speccify-desktop tauri signer generate -w ~/.speccify/update-signing/updater.key
   gh secret set TAURI_SIGNING_PRIVATE_KEY < ~/.speccify/update-signing/updater.key
   gh secret set TAURI_SIGNING_PRIVATE_KEY_PASSWORD   # falls beim Generieren gesetzt
   gh variable set TAURI_UPDATER_PUBKEY --body "<der ausgegebene Public Key>"
   ```

   Den Public Key zusätzlich in `tauri.conf.json` unter
   `plugins.updater.pubkey` eintragen (siehe [Updater](#updater) unten) —
   das ist der einzige Wert, der ins Repo gehört, er ist öffentlich.

### Windows (SmartScreen): Azure Trusted Signing — 3 Schritte

**Empfehlung: [Azure Trusted Signing](https://azure.microsoft.com/products/trusted-signing)**
(Basic ~10 $/Monat). Gründe: kein Zertifikats-Handling (kurzlebige
Zertifikate, automatisch rotiert), kein Hardware-Token — klassische
OV-Zertifikate müssen seit 2023 auf Token/HSM liegen und sind aus CI heraus
kaum nutzbar —, Microsoft-eigene Root, und SmartScreen-Reputation baut sich
deutlich schneller auf. Die Alternative (Certum „Open Source Code Signing",
~70 €/Jahr + Kartenleser) lohnt nur, wenn kein Azure-Konto infrage kommt.
Seit 2024 können auch Einzelpersonen (nicht nur Firmen) validiert werden.

1. **Azure einrichten**: Azure-Konto → Ressource *Trusted Signing Account*
   anlegen (Region merken, z. B. `weu`) → *Identity Validation* durchlaufen
   (Einzelperson oder Organisation) → *Certificate Profile* vom Typ
   *Public Trust* anlegen.
2. **Service Principal für CI**: Microsoft Entra → *App registration*
   anlegen, ein Client-Secret erzeugen, und der App auf dem Trusted-Signing-
   Konto die Rolle **Trusted Signing Certificate Profile Signer** geben.
3. **Secrets hinterlegen** — genau die sechs, auf die `release.yml` prüft:

   ```bash
   gh secret set AZURE_TENANT_ID       # Entra: Directory (tenant) ID
   gh secret set AZURE_CLIENT_ID       # App registration: Application (client) ID
   gh secret set AZURE_CLIENT_SECRET   # das erzeugte Client-Secret
   gh secret set AZURE_TS_ENDPOINT     # z. B. https://weu.codesigning.azure.net
   gh secret set AZURE_TS_ACCOUNT      # Name des Trusted-Signing-Accounts
   gh secret set AZURE_TS_PROFILE      # Name des Certificate Profile
   ```

Der `release-windows`-Job signiert dann Exe, Sidecars und die Installer
(NSIS + MSI) über `trusted-signing-cli`; ohne die Secrets baut er weiter
unsigniert.

**Das Azure-Setup muss nicht vom Repo-Inhaber kommen.** Die Pipeline kennt
keinen Tenant — sie liest nur die sechs Secrets. Ein Teammitglied mit
bestehendem Azure-Zugang kann Schritt 1–2 in seinem Tenant erledigen und
die Werte übergeben (oder als Repo-Admin selbst setzen). Zwei Dinge dabei
bewusst entscheiden:

- **Der Publisher-Name kommt aus der Identity Validation.** Windows zeigt
  als „Verifizierter Herausgeber" den validierten Namen — bei
  Org-Validation also die Firma des Teammitglieds, nicht „Speccify". Das
  muss der Name sein, der dauerhaft unter der App stehen soll: ein
  späterer Wechsel der Identität heißt neues Zertifikat und
  SmartScreen-Reputation von vorn.
- **Kosten und Kontrolle** laufen über dessen Azure-Subscription; für die
  Rollenzuweisung (*Trusted Signing Certificate Profile Signer* an die App
  Registration) braucht es dort Owner-/User-Access-Admin-Rechte.

### Linux (AppImage, deb, rpm) — keine Signierung nötig

Der Job `release-linux` (ubuntu-22.04, x86_64) baut `.AppImage`, `.deb`
und `.rpm` und hängt sie an denselben Draft. Ubuntu 22.04 statt -latest
ist Absicht: das AppImage wird gegen die ältere glibc/WebKitGTK gelinkt
und läuft dann auch auf Distributionen von 2022. Linux kennt weder
Gatekeeper noch SmartScreen — es gibt nichts scharf zu schalten; der
Updater (AppImage) läuft wie auf macOS nur mit den `TAURI_SIGNING_*`-
Secrets. Systemabhängigkeiten des Builds stehen im Job (WebKitGTK 4.1,
GTK 3, Ayatana-Appindicator, rsvg, patchelf, libfuse2 fürs AppImage-
Werkzeug). **Testlauf ohne Tag:** Workflow „Linux bundle (test build)"
per *Run workflow* starten — er baut dieselben Pakete als Artefakte des
Laufs. Der CI-Job `desktop-linux` (ci.yml) kompiliert und testet das
Desktop-Crate bei jedem Push auf Linux. Laufzeit-Voraussetzungen und die
Liste der Fälle, in denen es nicht läuft (WebKitGTK 4.0-Distributionen,
AppImage ohne libfuse2, Wayland+NVIDIA, headless, ARM), stehen auf der
Download-Seite.

### Danach

- **Draft veröffentlichen — per CLI, nicht im Browser.** Der Draft stammt
  vom Actions-Bot; „Publish release" in der Weboberfläche scheitert dann
  mit *author does not have push access* (GitHub prüft den Autor des
  Drafts, nicht den Klickenden). Stattdessen:

  ```bash
  gh release edit vX.Y.Z --draft=false
  ```

  Beim ersten Release (v0.4.0, 2026-09-05) so gelöst.
- **Website je Plattform umschalten**: nach verifiziertem macOS-Release
  `gh variable set PUBLIC_MACOS_RELEASE_SIGNED --body true`; Windows separat
  über `PUBLIC_WINDOWS_RELEASE_SIGNED` erst nach verifizierter Codesignatur.
  Die Download-Seite lässt nur die jeweilige Warnbox weg (nächster Pages-Deploy).
  Ein signierter Mac-Build sagt nichts über die Windows-Signatur aus.
- **Release-Text**: Der Release-Body in `release.yml` erklärt derzeit die
  Warnungen unsignierter Builds — nach dem ersten signierten Release die
  Absätze dort entfernen (und im Draft-Release vor dem Veröffentlichen
  gegenlesen, das bleibt ohnehin der letzte menschliche Blick).
- **Endtest**: je ein Artefakt auf einer fremden Maschine per Browser laden
  und starten — macOS ohne Gatekeeper-Dialog, Windows ohne SmartScreen-Blau.
  (SmartScreen kann trotz gültiger Signatur anfangs noch warnen, bis
  Reputation da ist — mit Trusted Signing typisch Tage, nicht Monate.)

---

Damit macOS die heruntergeladene App startet, braucht sie beides:

1. **Code Signing** mit einem *Developer ID Application*-Zertifikat
   (Apple Developer Program, 99 $/Jahr) und Hardened Runtime.
2. **Notarisierung**: Apple prüft das signierte Bundle automatisch und stellt
   ein Ticket aus, das ans Bundle geheftet („gestapelt") wird.

Ohne beides zeigt Gatekeeper „… kann nicht geöffnet werden, da der Entwickler
nicht verifiziert werden kann" — auch bei korrekt gebauter App.

## Einmalige Einrichtung

### 1. Zertifikat

Im [Apple Developer Portal](https://developer.apple.com/account/resources/certificates)
ein **Developer ID Application**-Zertifikat erzeugen und in den Login-Keychain
importieren (Doppelklick auf die `.cer`, privater Schlüssel muss dabei sein).
Prüfen:

```bash
security find-identity -v -p codesigning
# → 1) ABC123…  "Developer ID Application: Dein Name (TEAMID)"
```

Der vollständige String in Anführungszeichen ist die Signing-Identity.

### 2. Notarisierungs-Credentials

Zwei Wege — für lokale Releases reicht der erste:

**Apple ID + App-Specific Password** (auf
[appleid.apple.com](https://appleid.apple.com) unter „App-spezifische
Passwörter" erzeugen):

```bash
export APPLE_ID="deine@apple-id.tld"
export APPLE_PASSWORD="abcd-efgh-ijkl-mnop"   # App-Specific Password, NICHT das Account-Passwort
export APPLE_TEAM_ID="TEAMID"                  # steht in Klammern in der Identity
```

**App Store Connect API-Key** (besser für CI, kein Passwort im Klartext):

```bash
export APPLE_API_ISSUER="…-…-…"
export APPLE_API_KEY="ABC123XYZ"
export APPLE_API_KEY_PATH="$HOME/.appstoreconnect/AuthKey_ABC123XYZ.p8"
```

### 3. Signing-Identity setzen

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Dein Name (TEAMID)"
```

> **Nie ins Repo.** Keine dieser Variablen gehört in eine Datei unter
> Versionskontrolle. Praktisch: ein `~/.speccify/release.env`, das vor dem
> Release gesourct wird (`source ~/.speccify/release.env`), oder die Werte im
> Keychain halten und beim Aufruf exportieren.

## Release bauen

```bash
source ~/.speccify/release.env      # Credentials in die Umgebung
./scripts/release_macos.sh
```

Das Skript

1. prüft Werkzeuge, Identity (wirklich im Keychain?) und Credentials —
   und bricht **vor** dem Compile ab, wenn etwas fehlt,
2. baut Sidecars und Engine-Payload (release),
3. ruft `tauri build`: signiert alle Binaries im Bundle mit Hardened Runtime,
   lädt es bei Apple hoch, wartet auf das Ergebnis und stapelt das Ticket,
4. verifiziert das Ergebnis (siehe unten).

Die Notarisierung dauert typisch 2–15 Minuten; Apple drosselt bei vielen
Uploads. Für einen schnellen Zwischentest ohne Apple-Runde:

```bash
./scripts/release_macos.sh --no-notarize   # nur signieren
./scripts/release_macos.sh --verify-only   # vorhandenes Bundle prüfen
```

Ergebnis: `target/release/bundle/macos/Speccify.app` und
`target/release/bundle/dmg/Speccify_<version>_aarch64.dmg`. Die Version kommt
aus `apps/desktop/src-tauri/tauri.conf.json` (`version`) — vor einem Release
dort hochziehen.

## Verifikation

`release_macos.sh` macht das automatisch; von Hand sind es diese Schritte:

```bash
APP=target/release/bundle/macos/Speccify.app

codesign --verify --deep --strict --verbose=2 "$APP"   # Signatur intakt
codesign -dv --verbose=4 "$APP"                        # Authority/TeamIdentifier
spctl -a -vvv -t exec "$APP"                           # Gatekeeper akzeptiert?
xcrun stapler validate "$APP"                          # Ticket angeheftet?
```

Bei einer fertigen Release-App steht in der `codesign`-Ausgabe eine
`Authority=Developer ID Application: …`, ein gesetzter `TeamIdentifier` und
`flags=…(runtime)`; `spctl` meldet `accepted` mit `source=Notarized Developer ID`.

**Die mitgelieferten Binaries zählen mit.** Im Bundle liegen neben der App
vier Sidecars (`speccify-exec-mcp`, `speccify-discovery-mcp`,
`speccify-parallels-mcp` und `uv`). Tauri signiert sie mit, das Skript prüft
jedes einzeln — ein unsigniertes Sidecar fällt bei der Notarisierung nicht
zwingend auf, wird aber später beim Start von Gatekeeper abgeschossen.
`uv` ist Fremdcode: es wird von unserer Developer ID **re**-signiert, was für
Developer-ID-Distribution zulässig und üblich ist.

Echter Endtest: das `.dmg` auf einen **anderen** Mac kopieren (oder per
Browser herunterladen, damit das Quarantäne-Flag gesetzt wird) und starten.
Lokal gebaute Artefakte haben kein Quarantäne-Flag und starten auch
unsigniert — das täuscht Erfolg vor. Nachstellen lässt sich das mit:

```bash
xattr -w com.apple.quarantine "0081;00000000;Safari;" /Pfad/zu/Speccify.dmg
```

## Was die App zur Laufzeit nachlädt

Die App bringt die Python-Engine als Payload mit, baut daraus aber beim
ersten Start per `uv` eine venv im Benutzerverzeichnis (siehe
[`toolkit.md`](./toolkit.md)). Diese Dateien sind **nicht** von uns signiert:

- Das ist zulässig — die venv läuft als eigener Prozess, nicht als Code in
  unserem Adressraum (Hardened Runtime schränkt nur Letzteres ein).
- Was dabei entsteht, ist nicht quarantänebehaftet (uv lädt es nicht per
  Browser), Gatekeeper prüft es also nicht.
- Beim ersten Release auf einem fremden Mac trotzdem explizit testen:
  Umgebungs-Tab → „Engine installieren" (der Composer ist zurückgebaut, Plan projektfenster.md D18).

`uv` selbst liegt seit R5.2.7 als vierter Sidecar im Bundle und wird
mitsigniert — ein systemweit installiertes `uv` ist keine Voraussetzung mehr.

## Typische Fehlerbilder

| Meldung | Ursache | Lösung |
|---|---|---|
| `The specified item could not be found in the keychain` | Identity nicht im Login-Keychain oder falsch geschrieben | `security find-identity -v -p codesigning`, String exakt übernehmen |
| `Team ID … is not associated with your account` | `APPLE_TEAM_ID` passt nicht zum Zertifikat | Team-ID aus der Klammer der Identity nehmen |
| `Unable to notarize: HTTP status 401` | App-Specific Password abgelaufen/falsch | neues Passwort auf appleid.apple.com erzeugen |
| `code has no resources but signature indicates they must be present` | unsigniertes/ad-hoc gebautes Bundle geprüft | mit gesetzter `APPLE_SIGNING_IDENTITY` neu bauen |
| Notarisierung meldet `Invalid`, Log nennt ein Binary | ein mitgeliefertes Binary ohne Hardened Runtime | `./scripts/release_macos.sh --verify-only` zeigt, welches |

Notarisierungs-Log zu einer Einreichung abrufen:

```bash
xcrun notarytool history --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD"
xcrun notarytool log <submission-id> --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD"
```

## Updater

Die App sucht beim Start und danach im gewählten Intervall (6 Stunden, täglich,
wöchentlich; Standard täglich). Unter **Umgebung → Updates** lassen sich Suche
und Intervall einstellen und eine manuelle Suche starten. Ein verfügbarer Stand
erscheint als Hinweis in den Fenstern. Download und Installation sind getrennte,
ausdrückliche Aktionen; Fortschritt, Abbruch und Fehler bleiben sichtbar.

Ein nativer Koordinator teilt Zustand und Download zwischen allen Fenstern.
Vor der Installation sperrt er die Oberflächen und verlangt eine Antwort von
jedem Fenster. Offene Editoren, bearbeitete Formulare, gespeicherte Entwürfe und
laufende Terminals/Aktionen blockieren den Neustart. Erst speichern, die
betroffenen Ansichten schließen und Prozesse beenden; dann erneut installieren.
Ein fehlgeschlagener Vorabcheck behält den geprüften Download. Ein App-Neustart
verwirft den Download im Arbeitsspeicher, die Sucheinstellungen bleiben erhalten.

### Schlüssel und Bootstrap

Update-Signaturen (minisign) sind unabhängig vom OS-Codesigning. Der öffentliche
Schlüssel ist in `apps/desktop/src-tauri/tauri.conf.json` versioniert und muss
mit der GitHub-Variable `TAURI_UPDATER_PUBKEY` übereinstimmen. Der private
Schlüssel liegt in `~/.speccify/update-signing/updater.key` (Dateimodus 0600,
Ordner 0700) und im GitHub-Secret `TAURI_SIGNING_PRIVATE_KEY`. Er wurde ohne
zusätzliches Schlüsselpasswort eingerichtet; Dateizugriff und GitHub-Secrets
schützen ihn. Eine verschlüsselte externe Sicherung muss der Schlüsselinhaber
aufbewahren. Nicht neu erzeugen: vorhandene Installationen vertrauen diesem Key.

**0.8.0 und ältere Builds besitzen keinen Prüfkey.** Sie brauchen einmalig einen
neuen Installer mit Updater. Ein Release allein kann diesen fehlenden Key nicht
nachträglich in eine bereits installierte 0.8-App bringen. Der Bootstrap-Release
ist gesondert freizugeben; Implementierung und Testfixtures sind kein
Veröffentlichungs- oder N→N+1-Installationsnachweis.

### Vollständiger Release-Feed

Der Workflow verlangt signierte Pakete für alle unterstützten Update-Ziele:

| Ziel | Update-Paket |
| --- | --- |
| macOS Apple Silicon | `Speccify_aarch64.app.tar.gz` |
| Windows x64 | `Speccify_<version>_x64-setup.exe` |
| Linux x64 | `Speccify_<version>_amd64.AppImage` |
| Linux arm64 | `Speccify_<version>_aarch64.AppImage` |

Linux deb/rpm werden über den Paketmanager aktualisiert. macOS Intel ist noch
kein Release-Ziel. Die Update-Signatur beseitigt keine Windows-SmartScreen-Warnung.

Die Plattform-Jobs laden Pakete und `.sig` hoch, schreiben aber selbst kein
Manifest. Erst nach allen vier erfolgreichen Jobs lädt `update-manifest` die
Pakete erneut, prüft Uploadstatus, Dateigröße, SHA-256, Downloadziel und echte
minisign-Signatur mit dem eingecheckten Public Key. Nur dann erzeugt
`scripts/build_update_manifest.py` das vollständige `latest.json` und hängt
es an den Release-Entwurf. Ein fehlendes oder beschädigtes Paket stoppt diesen
Schritt. Vor Veröffentlichung müssen alle Jobs und das Manifest geprüft sein.

GitHub liefert Entwurfs-Releases am REST-Tag-Endpunkt als 404. Deshalb zuerst
mit `gh release view <tag> --json databaseId` die ID auflösen und die Metadaten
über `/releases/<id>` lesen. Für eine erneute Manifest-Prüfung bereits gebauter
Pakete kann der Workflow auf `main` mit `tag=<tag>` und `verify_only=true`
gestartet werden. Dabei werden sämtliche Paket- und Signaturprüfungen erneut
ausgeführt, ohne die Installer neu zu bauen. Vor Veröffentlichung zusätzlich
die erfolgreichen Plattform-Builds des ursprünglichen Laufs prüfen.

Der zusätzliche macOS-Prüfjob notarisiert und stapelt das signierte DMG selbst.
Das Ticket der enthaltenen App allein genügt nicht für die Prüfung des
Installationsmediums. `stapler validate` und `spctl --type open` müssen für das
DMG bestehen; erst danach wird das Update-Manifest erzeugt. Die App-Archive
und ihre Update-Signaturen bleiben bei diesem Schritt unverändert.

Endpoint:
`https://github.com/mhennemeyer/speccify/releases/latest/download/latest.json`.
Das Manifest enthält Version ohne `v`, Release-Notizen, RFC-3339-Datum und pro
Plattform Download-URL sowie vollständigen Signaturinhalt. Die App bietet nur
neuere Versionen an. Offline- und Signaturfehler installieren nichts und lassen
sich wiederholen. Der Download wird erst nach erfolgreicher Signaturprüfung zur
Installation freigegeben.

### Prüfung

- `cargo test -p speccify-desktop`: echter Tauri-Client gegen lokalen Testserver;
  neuere/gleiche/ältere Version, signierte und manipulierte Nutzdaten, Offline-Fall,
  fehlende Fensterantworten und Installationsblocker.
- `uv run pytest tests/test_update_manifest.py`: Vollständigkeit, URL-Herkunft,
  Versionsformat und echte minisign-Prüfung (minisign muss installiert sein).
- `node scripts/test_updates.mjs` mit lokalem Vite-Testserver: persistierte
  Einstellungen, Download/Abbruch/Fehler, Editor-/Prozessschutz und Installationsklick.
  Native Installation ist in diesem Oberflächentest simuliert.
- Zur Plattformabnahme: installierte Version N aktualisieren, Neustart und
  wiederhergestellte Fenster prüfen. Dies auf macOS, Windows und Linux AppImage
  separat nachweisen. Testfixtures allein erfüllen diese Abnahme nicht.

## Noch offen

- **Intel/Universal**: gebaut wird derzeit nur `aarch64`. Für Intel-Macs
  bräuchte es einen Universal-Build (`--target universal-apple-darwin`) inkl.
  Sidecars für beide Architekturen.
