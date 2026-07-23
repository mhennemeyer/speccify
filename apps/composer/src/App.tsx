import { useCallback, useEffect, useState } from "react";

import { getSpecDetail, listSpecs, saveSpec, validateSpec, ApiError } from "./api";
import { BottomBar } from "./components/BottomBar";
import { Canvas } from "./components/Canvas";
import { Inspector } from "./components/Inspector";
import { Palette } from "./components/Palette";
import { addChild, docToYaml, newComposite, yamlToDoc } from "./doc";
import {
  fireEvent,
  mergedNodeProps,
  synthesizePayload,
  type WiredState,
} from "./simulate";
import type {
  ChildInfo,
  LogEntry,
  SpecDoc,
  SpecSummary,
  ValidationIssue,
} from "./types";

export function App() {
  const [specs, setSpecs] = useState<SpecSummary[]>([]);
  const [doc, setDoc] = useState<SpecDoc | null>(null);
  const [children, setChildren] = useState<Record<string, ChildInfo>>({});
  const [selection, setSelection] = useState<string | null>(null);
  const [wired, setWired] = useState<WiredState>({});
  const [eventLog, setEventLog] = useState<LogEntry[]>([]);
  const [issues, setIssues] = useState<ValidationIssue[] | null>(null);
  const [status, setStatus] = useState<string>("");

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

  const updateDoc = useCallback((next: SpecDoc) => {
    setDoc(next);
    setIssues(null);
  }, []);

  const handleNew = useCallback(
    (name: string, kind: "ui-component" | "app") => {
      setDoc(newComposite(name, kind));
      setChildren({});
      setSelection(null);
      setWired({});
      setEventLog([]);
      setIssues(null);
      setStatus(`Neue ${kind === "app" ? "App" : "Composite"} „${name}" angelegt.`);
    },
    [],
  );

  const handleOpen = useCallback(async (summary: SpecSummary) => {
    try {
      const detail = await getSpecDetail(summary.id);
      setDoc(yamlToDoc(detail.yaml));
      setChildren(detail.children);
      setSelection(null);
      setWired({});
      setEventLog([]);
      setIssues(null);
      setStatus(`„${detail.id}@${detail.version}" geladen.`);
    } catch (error) {
      setStatus(`Laden fehlgeschlagen: ${String(error)}`);
    }
  }, []);

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
        const { doc: next, alias } = addChild(doc, info);
        setChildren((current) => ({ ...current, [alias]: info }));
        updateDoc(next);
        setSelection(alias);
        setStatus(`„${detail.id}" als Knoten „${alias}" hinzugefügt.`);
      } catch (error) {
        setStatus(`Hinzufügen fehlgeschlagen: ${String(error)}`);
      }
    },
    [doc, updateDoc],
  );

  const handleFire = useCallback(
    (alias: string, eventName: string) => {
      if (!doc) return;
      const child = children[alias];
      if (!child) return;
      const merged = mergedPropsFor(alias);
      const payload = synthesizePayload(child, eventName, merged);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [doc, children, wired, log],
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
        setChildren(loaded);
        updateDoc(next);
        setWired({});
        setStatus("YAML übernommen.");
      } catch (error) {
        setStatus(`YAML nicht übernehmbar: ${String(error)}`);
      }
    },
    [updateDoc],
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
          mergedPropsFor={mergedPropsFor}
          onSelect={setSelection}
          onFire={handleFire}
        />
        <Inspector
          doc={doc}
          childrenInfo={children}
          selection={selection}
          onDocChange={updateDoc}
          onChildrenChange={setChildren}
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
