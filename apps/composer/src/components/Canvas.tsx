import type { ChildInfo, SpecDoc } from "../types";

interface CanvasProps {
  doc: SpecDoc | null;
  childrenInfo: Record<string, ChildInfo>;
  selection: string | null;
  mergedPropsFor: (alias: string) => Record<string, unknown>;
  onSelect: (alias: string) => void;
  onFire: (alias: string, eventName: string) => void;
}

export function Canvas({
  doc,
  childrenInfo,
  selection,
  mergedPropsFor,
  onSelect,
  onFire,
}: CanvasProps) {
  if (!doc) {
    return (
      <main className="canvas">
        <div className="empty-canvas">
          Links eine neue Composite/App anlegen — oder eine bestehende Spec öffnen.
        </div>
      </main>
    );
  }

  const tree = doc.composition?.tree ?? [];

  return (
    <main className="canvas">
      {tree.length === 0 ? (
        <div className="empty-canvas">
          Kinder über „+ als Kind" aus der Palette hinzufügen. Der Canvas rendert
          jede Komponente als interaktiven Mock (API-Vertrag interpretiert) — die
          Event-Chips feuern die Verdrahtung.
        </div>
      ) : null}
      {tree.map((node) => {
        const child = childrenInfo[node.node];
        const merged = mergedPropsFor(node.node);
        return (
          <MockNode
            key={node.node}
            alias={node.node}
            child={child}
            merged={merged}
            selected={selection === node.node}
            onSelect={() => onSelect(node.node)}
            onFire={(eventName) => onFire(node.node, eventName)}
          />
        );
      })}
    </main>
  );
}

interface MockNodeProps {
  alias: string;
  child: ChildInfo | undefined;
  merged: Record<string, unknown>;
  selected: boolean;
  onSelect: () => void;
  onFire: (eventName: string) => void;
}

function MockNode({ alias, child, merged, selected, onSelect, onFire }: MockNodeProps) {
  if (!child) {
    return (
      <div className={`mock-node${selected ? " selected" : ""}`} onClick={onSelect}>
        <div className="head">
          <strong>{alias}</strong>
          <span className="badge">Kind-Contract fehlt</span>
        </div>
      </div>
    );
  }
  return (
    <div className={`mock-node${selected ? " selected" : ""}`} onClick={onSelect}>
      <div className="head">
        <strong>{alias}</strong>
        <span>{child.title}</span>
        <span className="badge">
          {child.id}@{child.version}
        </span>
        <span className="badge accent">mock</span>
      </div>
      {child.api.props.length > 0 ? (
        <dl className="propgrid">
          {child.api.props.map((prop) => (
            <PropRow key={prop.name} name={prop.name} value={merged[prop.name]} />
          ))}
        </dl>
      ) : null}
      {child.api.slots.length > 0 ? (
        <div className="muted">Slots: {child.api.slots.map((slot) => slot.name).join(", ")}</div>
      ) : null}
      {child.api.events.length > 0 ? (
        <div className="chips">
          {child.api.events.map((event) => (
            <button
              key={event.name}
              className="chip"
              onClick={(clickEvent) => {
                clickEvent.stopPropagation();
                onFire(event.name);
              }}
            >
              ⚡ {event.name}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function PropRow({ name, value }: { name: string; value: unknown }) {
  return (
    <>
      <dt>{name}</dt>
      <dd>{value === undefined ? "—" : JSON.stringify(value)}</dd>
    </>
  );
}
