// Canvas — rendert den **generierten Mock**, nicht eine zweite Interpretation
// des API-Vertrags: jede Komponente im Baum ist die echte Mock-Komponente aus
// der Closure von `POST /api/v1/mock/draft` (siehe `mockRuntime.ts`).
//
// Der Composer liefert ihr nur, was er als Editor weiß: gemergte Props,
// Event-Callbacks (→ Wiring-Simulation + Log) und Slot-Inhalte (→ Slot-Zonen
// als Einfüge-Ziel). Alles Sichtbare — Prop-Darstellung, Event-Chips, Styles —
// kommt aus dem generierten Code. Was hier steht, steht später im Projekt.
//
// Zwei Modi: „Bearbeiten" (Baum mit Editor-Rahmen) und „Vorschau" (die
// Dokument-Mock-Komponente selbst, mit ihrer eigenen internen Verdrahtung —
// die ehrlichste Kontrolle, ob die Spec das tut, was sie soll).

import { Component, useState, type DragEvent, type ReactNode } from "react";

import { DRAG_NODE, DRAG_SPEC, dragKind } from "../dnd";
import type { SlotTarget } from "../doc";
import { camel, componentName, eventPropName, mockModulePath } from "../mockRuntime";
import type { MockBundleState } from "../useMockBundle";
import type { ChildInfo, EventContract, SpecDoc, TreeNodeData } from "../types";

export type CanvasMode = "edit" | "preview";

interface CanvasProps {
  doc: SpecDoc | null;
  childrenInfo: Record<string, ChildInfo>;
  selection: string | null;
  slotTarget: SlotTarget | null;
  bundle: MockBundleState;
  mode: CanvasMode;
  mergedPropsFor: (alias: string) => Record<string, unknown>;
  onSelect: (alias: string) => void;
  onFire: (alias: string, eventName: string, payload: Record<string, unknown>) => void;
  onSlotTargetToggle: (parentAlias: string, slot: string) => void;
  onModeChange: (mode: CanvasMode) => void;
  onOwnEmit: (eventName: string, payload: Record<string, unknown>) => void;
  onDropSpec: (specId: string, target: SlotTarget | null) => void;
  onDropNode: (alias: string, target: SlotTarget | null) => void;
}

// Schlüssel des gerade überfahrenen Drop-Ziels ("" = Canvas-Hintergrund).
const ROOT_DROP = "";

function targetKey(target: SlotTarget | null): string {
  return target ? `${target.parentAlias}.${target.slot}` : ROOT_DROP;
}

// Render-Kontext, der unverändert durch die Rekursion gereicht wird.
interface NodeContext {
  childrenInfo: Record<string, ChildInfo>;
  selection: string | null;
  slotTarget: SlotTarget | null;
  bundle: MockBundleState;
  dragOver: string | null;
  mergedPropsFor: (alias: string) => Record<string, unknown>;
  onSelect: (alias: string) => void;
  onFire: (alias: string, eventName: string, payload: Record<string, unknown>) => void;
  onSlotTargetToggle: (parentAlias: string, slot: string) => void;
  onDragOverTarget: (key: string | null) => void;
  onDrop: (event: DragEvent, target: SlotTarget | null) => void;
}

export function Canvas({
  doc,
  childrenInfo,
  selection,
  slotTarget,
  bundle,
  mode,
  mergedPropsFor,
  onSelect,
  onFire,
  onSlotTargetToggle,
  onModeChange,
  onOwnEmit,
  onDropSpec,
  onDropNode,
}: CanvasProps) {
  const [dragOver, setDragOver] = useState<string | null>(null);

  const handleDrop = (event: DragEvent, target: SlotTarget | null) => {
    event.preventDefault();
    event.stopPropagation();
    setDragOver(null);
    const kind = dragKind(event.dataTransfer);
    if (kind === "spec") onDropSpec(event.dataTransfer.getData(DRAG_SPEC), target);
    if (kind === "node") onDropNode(event.dataTransfer.getData(DRAG_NODE), target);
  };

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
    bundle,
    dragOver,
    mergedPropsFor,
    onSelect,
    onFire,
    onSlotTargetToggle,
    onDragOverTarget: setDragOver,
    onDrop: handleDrop,
  };

  return (
    <main
      className={`canvas${dragOver === ROOT_DROP ? " drop-target" : ""}`}
      onDragOver={(event) => {
        if (mode !== "edit" || !dragKind(event.dataTransfer)) return;
        event.preventDefault();
        setDragOver(ROOT_DROP);
      }}
      onDragLeave={(event) => {
        if (event.currentTarget === event.target) setDragOver(null);
      }}
      onDrop={(event) => (mode === "edit" ? handleDrop(event, null) : undefined)}
    >
      <div className="canvas-bar">
        <div className="tabs">
          <button
            className={mode === "edit" ? "active" : ""}
            onClick={() => onModeChange("edit")}
          >
            Bearbeiten
          </button>
          <button
            className={mode === "preview" ? "active" : ""}
            onClick={() => onModeChange("preview")}
          >
            Vorschau
          </button>
        </div>
        <span className="spacer" />
        <BundleStatus bundle={bundle} />
      </div>
      {mode === "preview" ? (
        <PreviewPane doc={doc} bundle={bundle} onOwnEmit={onOwnEmit} />
      ) : (
        <>
          {tree.length === 0 ? (
            <div className="empty-canvas">
              Kinder über „+ als Kind" aus der Palette hinzufügen. Der Canvas rendert
              den generierten Mock jeder Komponente — dieselben Dateien, die
              `speccify mock` schreibt.
            </div>
          ) : null}
          {tree.map((node) => (
            <MockNode key={node.node} node={node} ctx={ctx} />
          ))}
        </>
      )}
    </main>
  );
}

function BundleStatus({ bundle }: { bundle: MockBundleState }) {
  if (bundle.error) {
    return (
      <span className="badge warn" title={bundle.error}>
        {bundle.stale ? "Mock veraltet" : "Mock nicht baubar"}
      </span>
    );
  }
  if (!bundle.runtime) return <span className="muted">Mock wird gebaut …</span>;
  return <span className="badge accent">Mock live</span>;
}

// --- Baum-Modus ---------------------------------------------------------------

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

  const slotContent: Record<string, ReactNode> = {};
  for (const slot of child.api.slots) {
    const filled = node.slots?.[slot.name] ?? [];
    const target: SlotTarget = { parentAlias: alias, slot: slot.name };
    const isTarget =
      ctx.slotTarget?.parentAlias === alias && ctx.slotTarget.slot === slot.name;
    const isDragOver = ctx.dragOver === targetKey(target);
    slotContent[camel(slot.name)] = (
      <div
        className={`slot-zone${isTarget ? " target" : ""}${isDragOver ? " drop-target" : ""}`}
        onClick={(clickEvent) => {
          clickEvent.stopPropagation();
          ctx.onSlotTargetToggle(alias, slot.name);
        }}
        onDragOver={(dragEvent) => {
          if (!dragKind(dragEvent.dataTransfer)) return;
          dragEvent.preventDefault();
          dragEvent.stopPropagation();
          ctx.onDragOverTarget(targetKey(target));
        }}
        onDragLeave={(dragEvent) => {
          if (dragEvent.currentTarget === dragEvent.target) ctx.onDragOverTarget(null);
        }}
        onDrop={(dropEvent) => ctx.onDrop(dropEvent, target)}
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
            leer — Komponente hierher ziehen (oder anklicken und „+ als Kind")
          </span>
        ) : null}
      </div>
    );
  }

  const eventHandlers: Record<string, (payload?: unknown) => void> = {};
  for (const event of child.api.events) {
    eventHandlers[eventPropName(event.name)] = (payload?: unknown) =>
      ctx.onFire(alias, event.name, decodePayload(event, payload));
  }

  const merged = ctx.mergedPropsFor(alias);
  const props: Record<string, unknown> = {};
  for (const prop of child.api.props) {
    if (merged[prop.name] !== undefined) props[camel(prop.name)] = merged[prop.name];
  }

  const resolved = resolveComponent(ctx.bundle, child);

  return (
    <div className={`mock-node${selected ? " selected" : ""}`} onClick={select}>
      <div
        className="head"
        draggable
        title="Ziehen, um den Knoten samt Teilbaum umzuhängen"
        onDragStart={(dragEvent) => {
          dragEvent.stopPropagation();
          dragEvent.dataTransfer.setData(DRAG_NODE, alias);
          dragEvent.dataTransfer.effectAllowed = "move";
        }}
      >
        <span className="grip" aria-hidden="true">
          ⠿
        </span>
        <strong>{alias}</strong>
        <span>{child.title}</span>
        <span className="badge">
          {child.id}@{child.version}
        </span>
        <span className="badge accent">mock</span>
      </div>
      {resolved.component ? (
        <MockBoundary key={componentName(child.id)} label={child.id}>
          <resolved.component {...props} {...eventHandlers} {...slotContent} />
        </MockBoundary>
      ) : (
        <>
          <div className="mock-missing">{resolved.reason}</div>
          {Object.values(slotContent)}
        </>
      )}
    </div>
  );
}

interface ResolvedComponent {
  component: React.ComponentType<Record<string, unknown>> | null;
  reason: string;
}

function resolveComponent(bundle: MockBundleState, child: ChildInfo): ResolvedComponent {
  if (!bundle.runtime) {
    return { component: null, reason: bundle.error ?? "Mock wird gebaut …" };
  }
  const path = mockModulePath(child.id, child.kind);
  try {
    const component = bundle.runtime.component(path);
    if (component) return { component, reason: "" };
    return {
      component: null,
      reason:
        child.kind === "logic"
          ? `${child.id} ist ein logic-Mock (Fixtures, keine Darstellung).`
          : `${path} exportiert keine Mock-Komponente.`,
    };
  } catch (error) {
    return { component: null, reason: String(error) };
  }
}

function decodePayload(event: EventContract, raw: unknown): Record<string, unknown> {
  // Der generierte Mock liefert camelCase-Felder; die Spec-Semantik (Wiring,
  // Log) arbeitet auf den snake_case-Namen aus dem API-Vertrag.
  const source = (raw ?? {}) as Record<string, unknown>;
  const payload: Record<string, unknown> = {};
  for (const field of event.payload) payload[field.name] = source[camel(field.name)];
  return payload;
}

// --- Vorschau-Modus -----------------------------------------------------------

function PreviewPane({
  doc,
  bundle,
  onOwnEmit,
}: {
  doc: SpecDoc;
  bundle: MockBundleState;
  onOwnEmit: (eventName: string, payload: Record<string, unknown>) => void;
}) {
  if (!bundle.runtime || !bundle.entry) {
    return <div className="empty-canvas">{bundle.error ?? "Mock wird gebaut …"}</div>;
  }
  let component: React.ComponentType<Record<string, unknown>> | null = null;
  try {
    component = bundle.runtime.component(bundle.entry);
  } catch (error) {
    return <div className="empty-canvas">{String(error)}</div>;
  }
  if (!component) {
    return <div className="empty-canvas">{bundle.entry} exportiert keine Mock-Komponente.</div>;
  }

  const props: Record<string, unknown> = {};
  for (const prop of doc.api?.props ?? []) {
    if (prop.default !== undefined) props[camel(prop.name)] = prop.default;
  }
  for (const event of doc.api?.events ?? []) {
    props[eventPropName(event.name)] = (payload?: unknown) => {
      const fields = Object.keys(event.payload ?? {});
      const source = (payload ?? {}) as Record<string, unknown>;
      const decoded: Record<string, unknown> = {};
      for (const field of fields) decoded[field] = source[camel(field)];
      onOwnEmit(event.name, decoded);
    };
  }

  const Component = component;
  return (
    <div className="preview-pane">
      <p className="muted">
        Der Mock des Dokuments selbst ({bundle.entry}) — Verdrahtung läuft hier im
        generierten Code, nicht in der Composer-Simulation.
      </p>
      <MockBoundary key={bundle.entry} label={doc.id}>
        <Component {...props} />
      </MockBoundary>
    </div>
  );
}

// --- Fehlergrenze -------------------------------------------------------------

class MockBoundary extends Component<
  { label: string; children: ReactNode },
  { message: string | null }
> {
  constructor(props: { label: string; children: ReactNode }) {
    super(props);
    this.state = { message: null };
  }

  static getDerivedStateFromError(error: unknown) {
    return { message: String(error) };
  }

  render() {
    if (this.state.message !== null) {
      return (
        <div className="mock-missing">
          Mock „{this.props.label}" ist abgestürzt: {this.state.message}
        </div>
      );
    }
    return this.props.children;
  }
}
