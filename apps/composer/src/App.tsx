import { useCallback, useEffect, useRef, useState } from "react";

import { getSpecDetail, listSpecs, saveSpec, validateSpec, ApiError } from "./api";
import { BottomBar } from "./components/BottomBar";
import { Canvas, type CanvasMode } from "./components/Canvas";
import { Inspector } from "./components/Inspector";
import { Palette } from "./components/Palette";
import {
  addChild,
  docToYaml,
  findTreeNode,
  newComposite,
  removeChild,
  yamlToDoc,
  type SlotTarget,
} from "./doc";
import { fireEvent, mergedNodeProps, type WiredState } from "./simulate";
import { useMockBundle } from "./useMockBundle";
import type {
  ChildInfo,
  LogEntry,
  SpecDoc,
  SpecSummary,
  ValidationIssue,
} from "./types";

// Undo/Redo-Einheit: Dokument + Kind-Contracts gehören zusammen — ein Snapshot
// hält beides, damit z. B. „Kind entfernen" als EIN Schritt zurückrollt.
interface Snapshot {
  doc: SpecDoc | null;
  children: Record<string, ChildInfo>;
}

// Schnelle Folge-Edits (Tippen im Prop-Editor) werden zu einem Undo-Schritt
// zusammengefasst, wenn sie innerhalb dieses Fensters liegen.
const COALESCE_WINDOW_MS = 800;
const HISTORY_LIMIT = 100;

export function App() {
  const [specs, setSpecs] = useState<SpecSummary[]>([]);
  const [doc, setDoc] = useState<SpecDoc | null>(null);
  const [children, setChildren] = useState<Record<string, ChildInfo>>({});
  const [selection, setSelection] = useState<string | null>(null);
  const [wired, setWired] = useState<WiredState>({});
  const [eventLog, setEventLog] = useState<LogEntry[]>([]);
  const [issues, setIssues] = useState<ValidationIssue[] | null>(null);
  const [status, setStatus] = useState<string>("");
  const [past, setPast] = useState<Snapshot[]>([]);
  const [future, setFuture] = useState<Snapshot[]>([]);
  const [slotTarget, setSlotTarget] = useState<SlotTarget | null>(null);
  const [canvasMode, setCanvasMode] = useState<CanvasMode>("edit");
  const lastPushRef = useRef(0);

  // Der Canvas rendert die generierte Mock-Closure des aktuellen Dokuments.
  const bundle = useMockBundle(doc);

  const refreshPalette = useCallback(async () => {
    try {
      setSpecs(await listSpecs());
    } catch (error) {
      setStatus(`Palette-Fehler: ${String(error)}`);
    }
  }, []);

  useEffect(() => {
    void refreshPalette();
  }, [refreshPalette]);

  const log = useCallback((entry: LogEntry) => {
    setEventLog((entries) => [...entries.slice(-199), entry]);
  }, []);

  // --- Undo/Redo -------------------------------------------------------------

  const pushHistory = useCallback((snapshot: Snapshot, coalesce = false) => {
    const now = Date.now();
    const withinBurst = coalesce && now - lastPushRef.current < COALESCE_WINDOW_MS;
    lastPushRef.current = coalesce ? now : 0;
    setFuture([]);
    if (withinBurst) return;
    setPast((entries) => [...entries.slice(-(HISTORY_LIMIT - 1)), snapshot]);
  }, []);

  const restoreSnapshot = useCallback((snapshot: Snapshot) => {
    setDoc(snapshot.doc);
    setChildren(snapshot.children);
    setWired({});
    setIssues(null);
    setSlotTarget(null);
    setSelection((current) =>
      current && findTreeNode(snapshot.doc?.composition?.tree ?? [], current)
        ? current
        : null,
    );
    lastPushRef.current = 0;
  }, []);

  const handleUndo = useCallback(() => {
    if (past.length === 0) return;
    const snapshot = past[past.length - 1];
    setPast(past.slice(0, -1));
    setFuture((entries) => [...entries, { doc, children }]);
    restoreSnapshot(snapshot);
    setStatus("Rückgängig gemacht.");
  }, [past, doc, children, restoreSnapshot]);

  const handleRedo = useCallback(() => {
    if (future.length === 0) return;
    const snapshot = future[future.length - 1];
    setFuture(future.slice(0, -1));
    setPast((entries) => [...entries, { doc, children }]);
    restoreSnapshot(snapshot);
    setStatus("Wiederholt.");
  }, [future, doc, children, restoreSnapshot]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "z") return;
      // In Eingabefeldern gewinnt das native Text-Undo.
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      event.preventDefault();
      if (event.shiftKey) {
        handleRedo();
      } else {
        handleUndo();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleUndo, handleRedo]);

  // --- Dokument-Mutationen -----------------------------------------------------

  const updateDoc = useCallback(
    (next: SpecDoc) => {
      // Inspector-Edits: koalesziert, damit Tippen ein Undo-Schritt bleibt.
      pushHistory({ doc, children }, true);
      setDoc(next);
      setIssues(null);
    },
    [doc, children, pushHistory],
  );

  const handleNew = useCallback(
    (name: string, kind: "ui-component" | "app") => {
      pushHistory({ doc, children });
      setDoc(newComposite(name, kind));
      setChildren({});
      setSelection(null);
      setWired({});
      setEventLog([]);
      setIssues(null);
      setSlotTarget(null);
      setStatus(`Neue ${kind === "app" ? "App" : "Composite"} „${name}" angelegt.`);
    },
    [doc, children, pushHistory],
  );

  const handleOpen = useCallback(
    async (summary: SpecSummary) => {
      try {
        const detail = await getSpecDetail(summary.id);
        pushHistory({ doc, children });
        setDoc(yamlToDoc(detail.yaml));
        setChildren(detail.children);
        setSelection(null);
        setWired({});
        setEventLog([]);
        setIssues(null);
        setSlotTarget(null);
        setStatus(`„${detail.id}@${detail.version}" geladen.`);
      } catch (error) {
        setStatus(`Laden fehlgeschlagen: ${String(error)}`);
      }
    },
    [doc, children, pushHistory],
  );

  const handleAddChild = useCallback(
    async (summary: SpecSummary) => {
      if (!doc) {
        setStatus("Erst eine Composite/App anlegen oder öffnen.");
        return;
      }
      try {
        const detail = await getSpecDetail(summary.id);
        const info: ChildInfo = {
          id: detail.id,
          version: detail.version,
          kind: detail.kind,
          title: detail.title,
          api: detail.api,
        };
        // Aktives Einfüge-Ziel (Slot-Zone im Canvas) gewinnt; sonst Top-Level.
        const target =
          slotTarget && findTreeNode(doc.composition?.tree ?? [], slotTarget.parentAlias)
            ? slotTarget
            : null;
        const { doc: next, alias } = addChild(doc, info, target);
        pushHistory({ doc, children });
        setChildren((current) => ({ ...current, [alias]: info }));
        setDoc(next);
        setIssues(null);
        setSelection(alias);
        setStatus(
          target
            ? `„${detail.id}" als Knoten „${alias}" in Slot ${target.parentAlias}.${target.slot} eingefügt.`
            : `„${detail.id}" als Knoten „${alias}" hinzugefügt.`,
        );
      } catch (error) {
        setStatus(`Hinzufügen fehlgeschlagen: ${String(error)}`);
      }
    },
    [doc, children, slotTarget, pushHistory],
  );

  const handleRemoveNode = useCallback(
    (alias: string) => {
      if (!doc) return;
      pushHistory({ doc, children });
      const next = removeChild(doc, alias);
      setDoc(next);
      setIssues(null);
      // Kind-Contracts aller entfernten Aliase (inkl. Slot-Teilbaum) wegräumen.
      const remaining = new Set(Object.keys(next.composition?.uses ?? {}));
      setChildren((current) =>
        Object.fromEntries(Object.entries(current).filter(([key]) => remaining.has(key))),
      );
      setSelection(null);
      setSlotTarget((current) => (current?.parentAlias === alias ? null : current));
      setStatus(`Knoten „${alias}" entfernt.`);
    },
    [doc, children, pushHistory],
  );

  const handleSlotTargetToggle = useCallback(
    (parentAlias: string, slot: string) => {
      const next =
        slotTarget?.parentAlias === parentAlias && slotTarget.slot === slot
          ? null
          : { parentAlias, slot };
      setSlotTarget(next);
      setStatus(
        next
          ? `Einfüge-Ziel: Slot ${parentAlias}.${slot} — „+ als Kind" fügt hier ein.`
          : `Einfüge-Ziel aufgehoben — „+ als Kind" fügt auf Top-Level ein.`,
      );
    },
    [slotTarget],
  );

  const handleFire = useCallback(
    (alias: string, eventName: string, payload: Record<string, unknown>) => {
      if (!doc) return;
      const child = children[alias];
      if (!child) return;
      log({ kind: "trigger", text: `⚡ ${alias}.${eventName} ${JSON.stringify(payload)}` });
      const result = fireEvent(doc, children, wired, ownPropValues(doc), alias, eventName, payload);
      setWired(result.state);
      for (const entry of result.setLog) {
        log({ kind: "set", text: `↦ ${entry}` });
      }
      for (const emittedEvent of result.emitted) {
        log({
          kind: "emit",
          text: `⇧ ${doc.id} emittiert ${emittedEvent.event} ${JSON.stringify(emittedEvent.payload)}`,
        });
      }
      if (result.emitted.length === 0 && result.setLog.length === 0) {
        log({ kind: "info", text: "· keine Wiring-Regel getroffen" });
      }
    },
    [doc, children, wired, log],
  );

  // Vorschau-Modus: das Dokument-Mock verdrahtet intern selbst und ruft nur noch
  // die eigenen Event-Callbacks — die landen im selben Log.
  const handleOwnEmit = useCallback(
    (eventName: string, payload: Record<string, unknown>) => {
      log({
        kind: "emit",
        text: `⇧ ${doc?.id ?? "Dokument"} emittiert ${eventName} ${JSON.stringify(payload)}`,
      });
    },
    [doc, log],
  );

  const mergedPropsFor = useCallback(
    (alias: string): Record<string, unknown> => {
      if (!doc) return {};
      return mergedNodeProps(doc, alias, children, wired, ownPropValues(doc));
    },
    [doc, children, wired],
  );

  const handleValidate = useCallback(async (): Promise<boolean> => {
    if (!doc) return false;
    try {
      const outcome = await validateSpec(docToYaml(doc));
      setIssues(outcome.issues);
      setStatus(outcome.ok ? "Validierung: ✓ sauber." : `Validierung: ${outcome.issues.length} Problem(e).`);
      return outcome.ok;
    } catch (error) {
      setStatus(`Validierung fehlgeschlagen: ${String(error)}`);
      return false;
    }
  }, [doc]);

  const handleSave = useCallback(async () => {
    if (!doc) return;
    const ok = await handleValidate();
    if (!ok) return;
    try {
      const saved = await saveSpec(docToYaml(doc));
      setStatus(`Gespeichert: ${saved.id}@${saved.version} → ${saved.path}`);
      await refreshPalette();
    } catch (error) {
      if (error instanceof ApiError) {
        setStatus(`Speichern abgelehnt (${error.status}): ${error.message}`);
      } else {
        setStatus(`Speichern fehlgeschlagen: ${String(error)}`);
      }
    }
  }, [doc, handleValidate, refreshPalette]);

  const handleApplyYaml = useCallback(
    async (yamlText: string) => {
      try {
        const next = yamlToDoc(yamlText);
        // Kind-Contracts für unbekannte Aliase nachladen (Round-Trip).
        const uses = next.composition?.uses ?? {};
        const loaded: Record<string, ChildInfo> = {};
        for (const [alias, ref] of Object.entries(uses)) {
          const specId = ref.startsWith("@") ? `@${ref.slice(1).split("@")[0]}` : ref;
          const detail = await getSpecDetail(specId);
          loaded[alias] = {
            id: detail.id,
            version: detail.version,
            kind: detail.kind,
            title: detail.title,
            api: detail.api,
          };
        }
        pushHistory({ doc, children });
        setChildren(loaded);
        setDoc(next);
        setIssues(null);
        setWired({});
        setSlotTarget(null);
        setStatus("YAML übernommen.");
      } catch (error) {
        setStatus(`YAML nicht übernehmbar: ${String(error)}`);
      }
    },
    [doc, children, pushHistory],
  );

  return (
    <>
      <header className="topbar">
        <h1>Speccify Composer</h1>
        {doc ? (
          <span className="badge accent">
            {doc.id}@{doc.version} · {doc.kind}
          </span>
        ) : (
          <span className="muted">keine Spec geöffnet</span>
        )}
        <div className="spacer" />
        <span className="muted">{status}</span>
        <button
          onClick={handleUndo}
          disabled={past.length === 0}
          aria-label="Rückgängig"
          title="Rückgängig (⌘Z / Ctrl+Z)"
        >
          ↩︎
        </button>
        <button
          onClick={handleRedo}
          disabled={future.length === 0}
          aria-label="Wiederholen"
          title="Wiederholen (⇧⌘Z / Shift+Ctrl+Z)"
        >
          ↪︎
        </button>
        <button onClick={() => void handleValidate()} disabled={!doc}>
          Validieren
        </button>
        <button className="primary" onClick={() => void handleSave()} disabled={!doc}>
          Speichern
        </button>
      </header>
      <div className="layout">
        <Palette
          specs={specs}
          onNew={handleNew}
          onOpen={(summary) => void handleOpen(summary)}
          onAddChild={(summary) => void handleAddChild(summary)}
        />
        <Canvas
          doc={doc}
          childrenInfo={children}
          selection={selection}
          slotTarget={slotTarget}
          bundle={bundle}
          mode={canvasMode}
          mergedPropsFor={mergedPropsFor}
          onSelect={setSelection}
          onFire={handleFire}
          onSlotTargetToggle={handleSlotTargetToggle}
          onModeChange={setCanvasMode}
          onOwnEmit={handleOwnEmit}
        />
        <Inspector
          doc={doc}
          childrenInfo={children}
          selection={selection}
          onDocChange={updateDoc}
          onRemoveNode={handleRemoveNode}
          onSelectionChange={setSelection}
        />
      </div>
      <BottomBar
        doc={doc}
        issues={issues}
        eventLog={eventLog}
        onApplyYaml={(text) => void handleApplyYaml(text)}
        onResetSim={() => {
          setWired({});
          setEventLog([]);
        }}
      />
    </>
  );
}

function ownPropValues(doc: SpecDoc): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const prop of doc.api?.props ?? []) {
    if (prop.default !== undefined) values[prop.name] = prop.default;
  }
  return values;
}
