"use client";

import { useMemo, useState } from "react";

import type { RenderResult } from "@/lib/api";

import SpecEditor from "./SpecEditor";

/**
 * Right-hand pane: shows the rendered files plus the `generator_pin` so the
 * playground makes determinism visible (model, prompt version, cache key,
 * seed) — that's the whole point of the offline-cache demo.
 */
export interface RenderOutputProps {
  result: RenderResult | null;
}

export default function RenderOutput({ result }: RenderOutputProps) {
  const fileNames = useMemo(
    () => (result ? Object.keys(result.files).sort() : []),
    [result],
  );
  const [activeFile, setActiveFile] = useState<string | null>(null);

  if (!result) {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#6b7280",
          border: "1px dashed #2a2f35",
          borderRadius: 6,
        }}
      >
        Click “Render React” to see the generated TSX.
      </div>
    );
  }

  const currentFile = activeFile ?? fileNames[0] ?? null;
  const currentContent = currentFile ? result.files[currentFile] : "";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, height: "100%" }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {fileNames.map((name) => {
          const active = name === currentFile;
          return (
            <button
              key={name}
              type="button"
              onClick={() => setActiveFile(name)}
              style={{
                padding: "0.25rem 0.625rem",
                background: active ? "#3b82f6" : "#1a1d21",
                color: active ? "white" : "#a8b0b8",
                border: "1px solid #2a2f35",
                borderRadius: 4,
                fontSize: "0.8125rem",
                cursor: "pointer",
              }}
            >
              {name}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => {
            if (currentContent) void navigator.clipboard.writeText(currentContent);
          }}
          style={{
            marginLeft: "auto",
            padding: "0.25rem 0.625rem",
            background: "#1a1d21",
            color: "#a8b0b8",
            border: "1px solid #2a2f35",
            borderRadius: 4,
            fontSize: "0.8125rem",
            cursor: "pointer",
          }}
        >
          Copy
        </button>
      </div>

      <div style={{ flex: 1, minHeight: 280 }}>
        <SpecEditor
          value={currentContent}
          language="typescript"
          readOnly
          height="100%"
        />
      </div>

      {result.generator_pin && (
        <details
          style={{
            background: "#1a1d21",
            border: "1px solid #2a2f35",
            borderRadius: 6,
            padding: "0.5rem 0.75rem",
            fontSize: "0.8125rem",
          }}
        >
          <summary style={{ cursor: "pointer", color: "#a8b0b8" }}>
            generator_pin · {result.generator_pin.model}
          </summary>
          <pre
            style={{
              marginTop: 8,
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
              color: "#e6e8eb",
            }}
          >
            {JSON.stringify(result.generator_pin, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
