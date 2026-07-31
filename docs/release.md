# Release: signierte Speccify.app für macOS

Speccify wird **außerhalb des App Store** verteilt (Plan
[`r5-distribution.md`](../.agent/plans/r5-distribution.md), D5): Download von
speccify.io statt Store, ohne Sandbox — der Exec-MCP und der Prozess-Supervisor
starten beliebige CLI-Befehle, das ginge sandboxed nicht.

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
drei Sidecars (`speccify-exec-mcp`, `speccify-discovery-mcp`,
`speccify-parallels-mcp`). Tauri signiert sie mit, das Skript prüft jedes
einzeln — ein unsigniertes Sidecar fällt bei der Notarisierung nicht
zwingend auf, wird aber später beim Start von Gatekeeper abgeschossen.

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
  Umgebungs-Tab → „Engine installieren" → Composer öffnen.

Offen aus R5.2: `uv` selbst liegt noch nicht im Bundle. Sobald es als
vierter Sidecar mitgeliefert wird, wird es mitsigniert und muss hier nicht
mehr gesondert vorausgesetzt werden.

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

## Noch offen (R5.4/R5.5)

- **Updater**: `tauri-plugin-updater` mit eigenem Signaturschlüssel und
  `latest.json` auf speccify.io — dann aktualisiert sich die App selbst.
- **Download-Seite** in `apps/marketing` mit dem dmg-Link.
- **Intel/Universal**: gebaut wird derzeit nur `aarch64`. Für Intel-Macs
  bräuchte es einen Universal-Build (`--target universal-apple-darwin`) inkl.
  Sidecars für beide Architekturen.
