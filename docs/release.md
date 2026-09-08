# Release: Speccify.app für macOS

> **Windows:** Der Job `release-windows` in `release.yml` baut auf demselben
> Tag einen x64-NSIS-Installer (`*-setup.exe`) plus MSI und hängt beide an
> dasselbe Draft-Release an. Ohne Azure-Secrets unsigniert — SmartScreen
> warnt beim ersten Start; mit den sechs `AZURE_*`-Secrets signiert der Job
> über Azure Trusted Signing (siehe Aktionsliste unten). Sidecars entstehen
> im Workflow selbst (pwsh, Release-Profil); das Engine-Payload-Skript läuft
> im Git-Bash des Runners.

Speccify wird **außerhalb des App Store** verteilt (Plan
[`r5-distribution.md`](../.agent/plans/archive/r5-distribution.md), D5): Download über
GitHub-Releases statt Store, ohne Sandbox — der Exec-MCP und der
Prozess-Supervisor starten beliebige CLI-Befehle, das ginge sandboxed nicht.

## Der normale Weg: ein Tag

`.github/workflows/release.yml` baut auf jedem `v*`-Tag: Sidecars,
Engine-Payload, `tauri build`, und legt einen **Entwurfs-Release** an. Der
letzte Blick auf das, was Nutzer bekommen, ist ein Mensch, der die
Release-Seite öffnet — nicht eine grüne Pipeline.

```bash
git tag v0.2.0 && git push origin v0.2.0
```

Ohne hinterlegte Secrets baut die Pipeline **unsigniert** und der Updater
bleibt inert. Das ist Absicht: eine Pipeline, die erst mit Apple-Konto läuft,
ist eine Pipeline, die man erst beim Launch zum ersten Mal testet. Welche
Secrets was freischalten, steht im Kopf des Workflows.

Das lokale Skript unten bleibt für Tests und für den Fall, dass man ohne CI
ausliefern will.

## Signierung scharf schalten — die Aktionsliste

Beide Release-Jobs sind fertig verdrahtet; es fehlen nur die Schlüssel.
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

4. **Updater-Schlüssel** (optional, schaltet Auto-Updates frei):

   ```bash
   pnpm --filter speccify-desktop tauri signer generate -w ~/.speccify/updater.key
   gh secret set TAURI_SIGNING_PRIVATE_KEY < ~/.speccify/updater.key
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
- **Website umschalten**: `gh variable set PUBLIC_RELEASE_SIGNED --body true`
  — die Download-Seite lässt die Gatekeeper/SmartScreen-Warnboxen weg
  (greift beim nächsten Pages-Deploy).
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

Die App kann sich selbst aktualisieren (`tauri-plugin-updater`). Das ist
**unabhängig von der Apple-Signatur**: Tauri signiert die Update-Artefakte
zusätzlich mit einem eigenen minisign-Schlüsselpaar, damit niemand ein
untergeschobenes Update einspielen kann.

### Schlüsselpaar erzeugen (einmalig)

```bash
pnpm --filter speccify-desktop tauri signer generate -w ~/.speccify/updater.key
```

Das schreibt den **privaten** Schlüssel nach `~/.speccify/updater.key` (mit
Passwort schützen, niemals ins Repo, nicht verlieren — ohne ihn kann keine
bestehende Installation mehr aktualisiert werden) und gibt den **Public Key**
aus. Diesen in `apps/desktop/src-tauri/tauri.conf.json` eintragen:

```jsonc
"plugins": {
  "updater": {
    "endpoints": ["https://github.com/mhennemeyer/speccify/releases/latest/download/latest.json"],
    "pubkey": "<hier der Public Key>"
  }
}
```

> Solange `pubkey` leer ist, hängt die App den Updater gar nicht erst ein und
> der Umgebungs-Tab zeigt „Automatische Updates sind in diesem Build nicht
> eingerichtet". Ein Build ohne Schlüssel bleibt damit voll funktionsfähig.

### Release mit Updater bauen

```bash
export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.speccify/updater.key)"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="…"     # falls gesetzt
./scripts/release_macos.sh
```

Ist der private Schlüssel gesetzt, schaltet das Skript
`bundle.createUpdaterArtifacts` ein und es entstehen zusätzlich:

```text
target/release/bundle/macos/Speccify.app.tar.gz       # das Update-Paket
target/release/bundle/macos/Speccify.app.tar.gz.sig   # dessen Signatur
```

Ohne Schlüssel wird bewusst **ohne** Updater-Artefakte gebaut (mit Hinweis) —
und wenn der Schlüssel gesetzt, aber kein `pubkey` eingetragen ist, bricht der
Preflight ab: sonst entstünden Updates, die keine Installation prüfen kann.

### `latest.json` auf speccify.io

Der Endpoint muss dieses JSON liefern (Tauri-2-Format):

```json
{
  "version": "0.2.0",
  "notes": "Kurze Release-Notes, werden in der App angezeigt.",
  "pub_date": "2026-08-01T10:00:00Z",
  "platforms": {
    "darwin-aarch64": {
      "signature": "<kompletter Inhalt von Speccify.app.tar.gz.sig>",
      "url": "https://github.com/mhennemeyer/speccify/releases/download/v0.2.0/Speccify_0.2.0_aarch64.app.tar.gz"
    }
  }
}
```

- `version` **ohne** führendes `v`; die App vergleicht mit ihrer eigenen
  Version aus `tauri.conf.json` und meldet nur höhere.
- `signature` ist der Dateiinhalt der `.sig`, nicht deren Pfad.
- `pub_date` ist RFC 3339.
- Für Intel-Macs käme `darwin-x86_64` dazu (siehe unten).
- Antwortet der Endpoint `204 No Content`, gilt das als „kein Update" —
  praktisch, um Updates kurzfristig zu stoppen.

Ablauf pro Release: bauen → `.app.tar.gz` und `.dmg` hochladen →
`latest.json` mit neuer Version, URL und Signatur aktualisieren. In der App:
Umgebungs-Tab → „Nach Updates suchen"; nach dem Einspielen muss Speccify
einmal neu gestartet werden.

## Noch offen

- **Intel/Universal**: gebaut wird derzeit nur `aarch64`. Für Intel-Macs
  bräuchte es einen Universal-Build (`--target universal-apple-darwin`) inkl.
  Sidecars für beide Architekturen.
