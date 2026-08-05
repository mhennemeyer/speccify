import { useState } from "react";

import { DRAG_SPEC } from "../dnd";
import type { IndexHit, SpecSummary } from "../types";

interface PaletteProps {
  specs: SpecSummary[];
  indexHits: IndexHit[];
  indexStatus: string;
  onNew: (name: string, kind: "ui-component" | "app") => void;
  onOpen: (summary: SpecSummary) => void;
  onAddChild: (specId: string) => void;
  onSearchIndex: (query: string) => void;
}

export function Palette({
  specs,
  indexHits,
  indexStatus,
  onNew,
  onOpen,
  onAddChild,
  onSearchIndex,
}: PaletteProps) {
  const [name, setName] = useState("my-widget");
  const [kind, setKind] = useState<"ui-component" | "app">("ui-component");
  const [query, setQuery] = useState("");

  return (
    <aside className="palette">
      <h2>Neu</h2>
      <div className="field">
        <label htmlFor="new-name">Name (@org/…)</label>
        <input
          id="new-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          pattern="[a-z0-9][a-z0-9-]*"
        />
      </div>
      <div className="field">
        <label htmlFor="new-kind">Art</label>
        <select
          id="new-kind"
          value={kind}
          onChange={(event) => setKind(event.target.value as "ui-component" | "app")}
        >
          <option value="ui-component">Composite-Komponente</option>
          <option value="app">App</option>
        </select>
      </div>
      <button className="primary" onClick={() => onNew(name, kind)}>
        Anlegen
      </button>

      <h2 style={{ marginTop: 20 }}>Palette (Registry)</h2>
      {specs.map((spec) => (
        <div
          className="palette-item"
          key={spec.id}
          draggable
          title="In den Canvas oder auf eine Slot-Zone ziehen"
          onDragStart={(event) => {
            event.dataTransfer.setData(DRAG_SPEC, spec.id);
            event.dataTransfer.effectAllowed = "copy";
          }}
        >
          <strong>{spec.title}</strong>
          <span className="meta">
            {spec.id}@{spec.version}
          </span>
          <div className="actions">
            <button className="small" onClick={() => onAddChild(spec.id)}>
              + als Kind
            </button>
            <button className="small" onClick={() => onOpen(spec)}>
              öffnen
            </button>
          </div>
        </div>
      ))}
      {specs.length === 0 ? <p className="muted">Keine Specs — läuft das Backend (:8000)?</p> : null}

      {/* Discovery: Specs aus Index-Repos, die gar nicht lokal liegen (P5). */}
      <h2 style={{ marginTop: 20 }}>Index (Discovery)</h2>
      <form
        className="field"
        onSubmit={(event) => {
          event.preventDefault();
          onSearchIndex(query);
        }}
      >
        <label htmlFor="index-query">Specs im Index suchen</label>
        <div className="row">
          <input
            id="index-query"
            value={query}
            placeholder="z. B. rating"
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="small" type="submit">
            Suchen
          </button>
        </div>
      </form>
      {indexStatus ? <p className="muted">{indexStatus}</p> : null}
      {indexHits.map((hit) => (
        <div
          className="palette-item index-item"
          key={hit.source}
          draggable
          title="In den Canvas oder auf eine Slot-Zone ziehen"
          onDragStart={(event) => {
            event.dataTransfer.setData(DRAG_SPEC, hit.source);
            event.dataTransfer.effectAllowed = "copy";
          }}
        >
          <strong>{hit.title}</strong>
          <span className="meta">{hit.source}</span>
          <span className="muted">{hit.summary}</span>
          <div className="actions">
            <button className="small" onClick={() => onAddChild(hit.source)}>
              + als Kind
            </button>
          </div>
        </div>
      ))}
    </aside>
  );
}
