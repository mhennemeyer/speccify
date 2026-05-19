"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import ErrorPanel from "@/components/ErrorPanel";
import RenderOutput from "@/components/RenderOutput";
import SpecEditor from "@/components/SpecEditor";
import SpecPicker, { specKey } from "@/components/SpecPicker";
import {
  type RenderResult,
  type SpecEntry,
  listSpecs,
  renderSpec,
} from "@/lib/api";

/**
 * Playground page — Phase 1d MVP.
 *
 * Layout: left = spec picker + YAML editor, right = render output. The render
 * call is client-triggered (button) and goes through Next's `/api/v1/*`
 * rewrite to the FastAPI backend. Editing the YAML invalidates the rendered
 * output and is expected to produce a `cache_miss` against the offline cache;
 * the `ErrorPanel` explains how to record a new cache entry.
 */
export default function PlaygroundPage() {
  const [specs, setSpecs] = useState<SpecEntry[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [yamlText, setYamlText] = useState<string>("");
  const [result, setResult] = useState<RenderResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [rendering, setRendering] = useState(false);

  // Initial fetch of registry-fixture specs.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const entries = await listSpecs();
        if (cancelled) return;
        setSpecs(entries);
        if (entries.length > 0) {
          const first = entries[0];
          setSelectedKey(specKey(first));
          setYamlText(first.yaml);
        }
      } catch (e) {
        if (!cancelled) setError(e);
      } finally {
        if (!cancelled) setLoadingList(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedEntry = useMemo(
    () => specs.find((s) => specKey(s) === selectedKey) ?? null,
    [specs, selectedKey],
  );

  const handleSelect = useCallback(
    (key: string) => {
      const next = specs.find((s) => specKey(s) === key);
      if (!next) return;
      setSelectedKey(key);
      setYamlText(next.yaml);
      setResult(null);
      setError(null);
    },
    [specs],
  );

  const handleRender = useCallback(async () => {
    if (!selectedEntry) return;
    setRendering(true);
    setError(null);
    setResult(null);
    try {
      const rendered = await renderSpec({
        specId: selectedEntry.id,
        version: selectedEntry.version,
        specYaml: yamlText,
        target: "react",
      });
      setResult(rendered);
    } catch (e) {
      setError(e);
    } finally {
      setRendering(false);
    }
  }, [selectedEntry, yamlText]);

  const yamlDirty = selectedEntry !== null && yamlText !== selectedEntry.yaml;

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        padding: "1rem 1.25rem",
        gap: "1rem",
      }}
    >
      <header style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Speccify Playground</h1>
        <span style={{ fontSize: "0.8125rem", color: "#6b7280" }}>
          offline · replay cache only
        </span>
      </header>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "1rem",
          flex: 1,
          minHeight: 0,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", minHeight: 0 }}>
          <SpecPicker
            specs={specs}
            selectedKey={selectedKey}
            onSelect={handleSelect}
            disabled={loadingList || rendering}
          />
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button
              type="button"
              onClick={handleRender}
              disabled={!selectedEntry || rendering}
              style={{
                padding: "0.5rem 1rem",
                background: rendering ? "#1d4ed8" : "#3b82f6",
                color: "white",
                border: "none",
                borderRadius: 6,
                fontSize: "0.9375rem",
                fontWeight: 600,
                cursor: rendering ? "wait" : "pointer",
                opacity: !selectedEntry || rendering ? 0.7 : 1,
              }}
            >
              {rendering ? "Rendering…" : "Render React"}
            </button>
            {yamlDirty && (
              <span style={{ fontSize: "0.8125rem", color: "#fbbf24" }}>
                Spec edited — cache miss expected
              </span>
            )}
          </div>
          <div style={{ flex: 1, minHeight: 280 }}>
            <SpecEditor
              value={yamlText}
              language="yaml"
              onChange={setYamlText}
              height="100%"
            />
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", minHeight: 0 }}>
          {error ? <ErrorPanel error={error} /> : null}
          <div style={{ flex: 1, minHeight: 280 }}>
            <RenderOutput result={result} />
          </div>
        </div>
      </section>
    </main>
  );
}
