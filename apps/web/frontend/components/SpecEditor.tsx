"use client";

import dynamic from "next/dynamic";

/**
 * Monaco-backed YAML editor.
 *
 * Lazy-loaded with `ssr: false` because Monaco depends on `window`. Read-only
 * mode is supported so the same component can also display the rendered TSX
 * in `RenderOutput`.
 */
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#6b7280",
      }}
    >
      Loading editor…
    </div>
  ),
});

export interface SpecEditorProps {
  value: string;
  language?: "yaml" | "typescript";
  onChange?: (value: string) => void;
  readOnly?: boolean;
  height?: string | number;
}

export default function SpecEditor({
  value,
  language = "yaml",
  onChange,
  readOnly = false,
  height = "100%",
}: SpecEditorProps) {
  return (
    <div
      style={{
        height,
        border: "1px solid #2a2f35",
        borderRadius: 6,
        overflow: "hidden",
        background: "#1a1d21",
      }}
    >
      <MonacoEditor
        value={value}
        language={language}
        theme="vs-dark"
        onChange={(next) => onChange?.(next ?? "")}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 13,
          scrollBeyondLastLine: false,
          wordWrap: "on",
          automaticLayout: true,
        }}
      />
    </div>
  );
}
