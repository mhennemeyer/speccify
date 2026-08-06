---
title: Deine erste Spec
description: Von der speccify.yaml zum lauffähigen Mock — in fünf Minuten.
---

Eine Spec beschreibt eine Komponente **sprach- und framework-unabhängig**:
was sie kann (`api:`), woraus sie besteht (`composition:`) und wie sie sich
verhalten soll (`acceptance:`). Aus dem `api:`-Block entsteht deterministisch
ein Mock — ohne LLM, ohne Netz.

## 1. Spec schreiben

```yaml
# specs/rating-stars.speccify.yaml
schema_version: 1
id: "@org/rating-stars"
version: 0.1.0
kind: ui-component
title: Rating Stars
summary: Sternebewertung mit halben Sternen und Tastaturbedienung.

api:
  props:
    - name: value
      type: number
      default: 0
    - name: readonly
      type: boolean
      default: false
  events:
    - name: rated
      payload:
        value: number

acceptance:
  - given: readonly=false
    when: Nutzer klickt den dritten Stern
    then: rated-Event mit value=3
```

```bash
uv run speccify lint specs/rating-stars.speccify.yaml
```

## 2. Mock generieren

```bash
uv run speccify mock @org/rating-stars --registry ./registry-fixtures --out ./mocks
```

Heraus kommt eine echte React-Komponente mit typisierten Props, Event-Chips
und Slots — austauschbar gegen die spätere Implementierung, weil beide
denselben API-Vertrag erfüllen. Details:
[API-Vertrag & Mocks](/concepts/api-and-mocks/).

## 3. Visuell komponieren

```bash
./scripts/dev-up.sh     # → http://localhost:5173
```

Der [Composer](/composer/) rendert genau diese Mocks: Komponenten
zusammenziehen, Events typgeprüft verdrahten, speichern — heraus kommt wieder
eine ganz normale `speccify.yaml`.

## 4. Ein Projekt daraus bauen

Eine Spec mit `kind: app` komponiert Screens zu einem lauffähigen Projekt:

```bash
uv run speccify build @org/demo-app --registry ./registry-fixtures --out ./demo-app
cd demo-app && pnpm install && pnpm dev
```

Mehr dazu: [Projekt-Builds](/app-builds/).

## 5. Teilen

Veröffentlichen heißt `git tag` + `git push` — kein Registry-Account:

```yaml
dependencies:
  "git+https://github.com/acme/rating-stars": "^0.1"
```

Mehr dazu: [Git-Quellen & Discovery](/git-sources/).
