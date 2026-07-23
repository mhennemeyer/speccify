import { useState } from "react";

import type { SpecSummary } from "../types";

interface PaletteProps {
  specs: SpecSummary[];
  onNew: (name: string, kind: "ui-component" | "app") => void;
  onOpen: (summary: SpecSummary) => void;
  onAddChild: (summary: SpecSummary) => void;
}

export function Palette({ specs, onNew, onOpen, onAddChild }: PaletteProps) {
  const [name, setName] = useState("my-widget");
  const [kind, setKind] = useState<"ui-component" | "app">("ui-component");

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
        <div className="palette-item" key={spec.id}>
          <strong>{spec.title}</strong>
          <span className="meta">
            {spec.id}@{spec.version}
          </span>
          <div className="actions">
            <button className="small" onClick={() => onAddChild(spec)}>
              + als Kind
            </button>
            <button className="small" onClick={() => onOpen(spec)}>
              öffnen
            </button>
          </div>
        </div>
      ))}
      {specs.length === 0 ? <p className="muted">Keine Specs — läuft das Backend (:8000)?</p> : null}
    </aside>
  );
}
