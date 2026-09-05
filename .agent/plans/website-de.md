---
lifecycle: draft
status: Entwurf — wartet auf BO-Entscheide D1–D6, dann S1
---
# Plan: speccify.de — die Website auf Deutsch unter eigener Domain

> **BO (2026-09-05):** „Ich hab auch die speccify.de Domain. Wäre schön,
> wenn wir die Website auch entsprechend auf Deutsch hätten."

## Ziel

Unter **speccify.de** erscheint die Website deutsch an der Wurzel
(`speccify.de/app/board/`), unter **speccify.io** weiter englisch an der
Wurzel. Beide Domains kommen aus **derselben Astro/Starlight-Quelle** in
`apps/marketing/`, jede Seite kennt ihr Gegenstück auf der anderen Domain
(`hreflang`, Sprachumschalter), und der Deploy bleibt „Push auf main".

## Ist-Stand (erhoben 2026-09-05)

**Sprachen heute:** Starlight mit `defaultLocale: "root"` (= Englisch) und
`de` als Präfix-Locale. Deutsche Fassungen gibt es vollständig für
`app` (6/6), `fundamentals` (4/4), `speccify` (5/5), `tutorial` (10/10)
sowie die Landing (`src/pages/de/index.astro`). **Nicht deutsch:**
`cli/` (13 Seiten, aus `speccify --help` generiert via
`scripts/gen_cli_docs.py`), `git-sources/` (1, aus `docs/` synchronisiert
via `scripts/sync_docs_to_site.py`), `mcp/` (1), die **Download-Seite**,
**Impressum/Datenschutz** (Platzhalter, englisch) und das
`MarketingLayout` (hart `lang="en"`, kein `hreflang`, kein `canonical`).
Build: 86 Seiten. `site: "https://speccify.io"` fest in `astro.config.mjs`,
`public/CNAME` = speccify.io.

**Deploy:** GitHub Pages aus dem Repo (Quelle `main`, `pages.yml`,
Custom Domain speccify.io, HTTPS erzwungen). `docs.yml` prüft Drift
(docs ↔ Site, CLI-Referenz), Links (lychee) und Markdown. **GitHub Pages
erlaubt genau eine Custom-Domain pro Repo** — speccify.de kann nicht
einfach dazu.

**DNS:** Beide Domains laufen über GoDaddy-Nameserver
(`domaincontrol.com`). speccify.io → die vier GitHub-Pages-IPs.
**speccify.de → 80.67.16.8** (antwortet mit nginx 500 — Parkplatz) und hat
**eigene MX-Einträge** (secureserver.net) — **MX nie anfassen**, dort
hängt Mail.

## Entscheidungen, die der BO treffen muss

* **D1 — Variante.** Empfehlung **B1** (siehe unten): zwei Builds aus einer
  Quelle, Deutsch an der Wurzel von .de, Englisch an der Wurzel von .io,
  keine URL-Änderung auf .io. Alternativen: **A** reine Weiterleitung
  `speccify.de → speccify.io/de/` (eine Stunde Arbeit, aber die .de taucht
  nie als Adresse auf); **B2** beide Sprachen als Präfix (`/en/`, `/de/`)
  auf beiden Domains — technisch am einfachsten, ändert aber alle
  bestehenden .io-URLs (`/app/board/` → `/en/app/board/`, mit
  Umleitungsseiten).
* **D2 — Hosting der .de.** Empfehlung: **zweites GitHub-Pages-Repo**
  `mhennemeyer/speccify-de` (nur Auslieferung, Branch `gh-pages`), aus
  dem Haupt-Repo per Deploy-Key bespielt — bleibt im GitHub-Kosmos, kein
  neuer Anbieter. Alternative: Cloudflare Pages (kostenlos, mehrere
  Domains je Projekt, aber ein weiterer Anbieter mit eigenem Login).
* **D3 — CLI-Referenz.** Empfehlung: bleibt auf der .de **englisch**
  (sie ist `--help`-Ausgabe; Starlight blendet den englischen Text mit
  Hinweis „Diese Seite ist noch nicht übersetzt" ein), nur die
  Einstiegsseite `cli/index` bekommt eine deutsche Fassung.
* **D4 — Impressum und Datenschutz.** Auf einer .de-Domain sind deutsche
  Rechtstexte Pflicht (Impressumspflicht § 5 DDG, DSGVO-Hinweis wegen
  Plausible). Texte kommen vom BO; im Plan sind sie als Platzhalter
  vorgesehen, aber **ohne Texte geht die .de nicht live**.
* **D5 — `www.speccify.de`.** Empfehlung wie bei .io: CNAME auf
  `mhennemeyer.github.io`, GitHub leitet auf den Apex um.
* **D6 — Plausible.** Eine gemeinsame Domain-Ansicht oder zwei? Empfehlung
  zwei (`PUBLIC_PLAUSIBLE_DOMAIN` je Build-Variante).

## Architektur (Variante B1)

**Ein Repo, eine Quelle, zwei Build-Varianten**, gesteuert über eine
Umgebungsvariable `SITE_LOCALE_ROOT=en|de`:

* `astro.config.mjs` liest die Variante: `site` (io/de), Starlight
  `defaultLocale`/`locales` (Wurzel = Variante, die andere Sprache als
  Präfix `en/` bzw. `de/`), `PUBLIC_PLAUSIBLE_DOMAIN`.
* **Inhaltsbaum wird zusammengesetzt, nicht dupliziert.** Starlight
  bindet Locales an Verzeichnisnamen; die Wurzel muss also je Variante
  eine andere Sprache enthalten. Kanonisch liegen die Inhalte künftig
  unter `apps/marketing/content/{en,de}/…`; ein Prebuild-Skript
  (`scripts/site_assemble.py`) baut daraus `src/content/docs/`
  (Wurzel = Variantensprache, andere Sprache im Präfix-Ordner) — der
  Ordner wird **generiert und gitignored**. Editiert wird nur noch unter
  `content/`. `sync_docs_to_site.py` und `gen_cli_docs.py` schreiben
  ebenfalls nach `content/en/…`.
* **Marketing-Seiten** (`src/pages`): `index`, `download`, `legal/*` als
  Sprachpaare unter `pages/en/` und `pages/de/`; die Wurzel-Routen sind
  dünne Wrapper, die je Variante die richtige Sprache rendern.
  `MarketingLayout` bekommt `lang`, `canonical` und `alternate`-Props.
* **Querverweise zwischen den Domains:** eine kleine Helferfunktion
  `alternateUrl(path, lang)` liefert die Adresse derselben Seite auf der
  anderen Domain. Sie speist `<link rel="alternate" hreflang>` (Starlight
  über eine `Head`-Komponenten-Überschreibung, Marketing-Seiten über das
  Layout) und den **Sprachumschalter** (Starlight-`LanguageSelect`
  überschreiben: statt `/de/…` auf derselben Domain → `speccify.de/…`).
* `public/CNAME` wird je Variante geschrieben (io/de), Sitemap und
  `robots.txt` je Variante.

## Meilensteine

**S1 — Zwei Builds aus einer Quelle (lokal).** Inhalte nach `content/`
verschieben (`git mv`, Historie bleibt), Assemble-Skript, Env-Variante in
`astro.config.mjs`, Marketing-Seiten als Sprachpaare, Layout mit `lang`.
*Fertig heißt:* `SITE_LOCALE_ROOT=en pnpm build` liefert byte-gleiche
Seiten wie heute (Diff gegen den aktuellen `dist/` = leer bis auf
`hreflang`/`canonical`); `SITE_LOCALE_ROOT=de pnpm build` liefert Deutsch
an der Wurzel; beide `astro preview`-Läufe per Playwright: Landing, eine
Docs-Seite je Sektion, Download — richtige Sprache, richtige
`<html lang>`, Sprachumschalter zeigt auf die andere Domain.

**S2 — Deutsche Lücken schließen.** Download-Seite (inkl. der
Gatekeeper-/SmartScreen-Hinweise), `git-sources`, `mcp`, `cli/index`
übersetzen; Impressum/Datenschutz mit BO-Text (D4); Prüfung, dass die
Starlight-Fallback-Hinweise auf der .de nur bei der CLI-Referenz
erscheinen. *Fertig heißt:* `pnpm build` (de) ohne Fallback außer `cli/*`,
lychee 0 tote Links in beiden Varianten, Rechtstexte stehen.

**S3 — Deploy und DNS.** `pages.yml` baut beide Varianten; die .io wie
bisher, die .de per `peaceiris/actions-gh-pages` mit
`external_repository: mhennemeyer/speccify-de` und Deploy-Key
(BO legt das Repo an, generiert den Key, hinterlegt ihn als Secret
`SITE_DE_DEPLOY_KEY` und den Public Key als Deploy-Key mit Schreibrecht
im Zielrepo). `docs.yml` baut beide Varianten als Gate. **DNS (BO, bei
GoDaddy):** die A-Records von speccify.de auf die vier GitHub-Pages-IPs
(185.199.108–111.153), `www` als CNAME auf `mhennemeyer.github.io.`,
den Park-A-Record 80.67.16.8 entfernen, **MX unverändert**. Im Zielrepo
Custom Domain `speccify.de` eintragen, nach dem Zertifikat HTTPS
erzwingen. *Fertig heißt:* `curl -I https://speccify.de/` → 200 mit
gültigem Zertifikat, `https://www.speccify.de` → Apex, Landing deutsch,
`speccify.io` unverändert englisch, Sprachumschalter springt zwischen
den Domains, `hreflang` beidseitig, Plausible zählt je Domain.

**S4 — Nacharbeit.** README und Release-Body nennen beide Adressen;
App-Hilfe/Download-Verweise prüfen; `docs/release.md` um den
Zwei-Domain-Deploy ergänzen; Plan archivieren.

## Nicht in diesem Plan

* Weitere Sprachen (die Struktur trägt sie, aber niemand übersetzt).
* Übersetzung der CLI-Referenz (D3).
* Ein CMS oder Übersetzungs-Workflow — Inhalte bleiben Markdown im Repo.

## Risiken und Fallen

* **Starlight bindet Locales an Ordnernamen** — deshalb der Assemble-
  Schritt. Wer direkt in `src/content/docs/` editiert, verliert die
  Änderung beim nächsten Build; der Ordner muss gitignored und im
  Drift-Check erwähnt sein.
* **Byte-gleicher .io-Build als Abnahmekriterium für S1** schützt vor
  stillen Regressionen beim Umzug der Inhalte.
* **MX auf speccify.de** — Mail hängt daran. Nur A/CNAME anfassen.
* **GitHub-Pages-Zertifikat** braucht nach der DNS-Änderung bis zu einer
  Stunde; „Enforce HTTPS" erst danach aktivierbar.
* **Doppelte Indexierung** ohne `hreflang`/`canonical` — deshalb
  Bestandteil von S1, nicht Nacharbeit.
