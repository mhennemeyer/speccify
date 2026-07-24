import type { SlotTarget } from "../doc";
import type { ChildInfo, SpecDoc, TreeNodeData } from "../types";

interface CanvasProps {
  doc: SpecDoc | null;
  childrenInfo: Record<string, ChildInfo>;
  selection: string | null;
  slotTarget: SlotTarget | null;
  mergedPropsFor: (alias: string) => Record<string, unknown>;
  onSelect: (alias: string) => void;
  onFire: (alias: string, eventName: string) => void;
  onSlotTargetToggle: (parentAlias: string, slot: string) => void;
}

// Render-Kontext, der unverändert durch die Rekursion gereicht wird.
interface NodeContext {
  childrenInfo: Record<string, ChildInfo>;
  selection: string | null;
  slotTarget: SlotTarget | null;
  mergedPropsFor: (alias: string) => Record<string, unknown>;
  onSelect: (alias: string) => void;
  onFire: (alias: string, eventName: string) => void;
  onSlotTargetToggle: (parentAlias: string, slot: string) => void;
}

export function Canvas({
  doc,
  childrenInfo,
  selection,
  slotTarget,
  mergedPropsFor,
  onSelect,
  onFire,
  onSlotTargetToggle,
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
  const ctx: NodeContext = {
    childrenInfo,
    selection,
    slotTarget,
    mergedPropsFor,
    onSelect,
    onFire,
    onSlotTargetToggle,
  };

  return (
    <main className="canvas">
      {tree.length === 0 ? (
        <div className="empty-canvas">
          Kinder über „+ als Kind" aus der Palette hinzufügen. Der Canvas rendert
          jede Komponente als interaktiven Mock (API-Vertrag interpretiert) — die
          Event-Chips feuern die Verdrahtung.
        </div>
      ) : null}
      {tree.map((node) => (
        <MockNode key={node.node} node={node} ctx={ctx} />
      ))}
    </main>
  );
}

function MockNode({ node, ctx }: { node: TreeNodeData; ctx: NodeContext }) {
  const alias = node.node;
  const child = ctx.childrenInfo[alias];
  const selected = ctx.selection === alias;
  const select = (clickEvent: React.MouseEvent) => {
    clickEvent.stopPropagation();
    ctx.onSelect(alias);
  };

  if (!child) {
    return (
      <div className={`mock-node${selected ? " selected" : ""}`} onClick={select}>
        <div className="head">
          <strong>{alias}</strong>
          <span className="badge">Kind-Contract fehlt</span>
        </div>
      </div>
    );
  }

  const merged = ctx.mergedPropsFor(alias);

  return (
    <div className={`mock-node${selected ? " selected" : ""}`} onClick={select}>
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
      {child.api.slots.map((slot) => {
        const filled = node.slots?.[slot.name] ?? [];
        const isTarget =
          ctx.slotTarget?.parentAlias === alias && ctx.slotTarget.slot === slot.name;
        return (
          <div
            key={slot.name}
            className={`slot-zone${isTarget ? " target" : ""}`}
            onClick={(clickEvent) => {
              clickEvent.stopPropagation();
              ctx.onSlotTargetToggle(alias, slot.name);
            }}
          >
            <div className="slot-label">
              Slot {slot.name}
              {slot.optional ? "" : " *"}
              {isTarget ? <span className="badge accent">Einfüge-Ziel</span> : null}
            </div>
            {filled.map((slotNode) => (
              <MockNode key={slotNode.node} node={slotNode} ctx={ctx} />
            ))}
            {filled.length === 0 ? (
              <span className="muted">
                leer — anklicken und dann „+ als Kind" aus der Palette
              </span>
            ) : null}
          </div>
        );
      })}
      {child.api.events.length > 0 ? (
        <div className="chips">
          {child.api.events.map((event) => (
            <button
              key={event.name}
              className="chip"
              onClick={(clickEvent) => {
                clickEvent.stopPropagation();
                ctx.onFire(alias, event.name);
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
