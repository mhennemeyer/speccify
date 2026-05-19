"use client";

import type { SpecEntry } from "@/lib/api";

/**
 * Dropdown to choose one of the registry-fixture specs returned by
 * `GET /api/v1/specs`. Stateless on purpose — parent owns the selection.
 */
export interface SpecPickerProps {
  specs: SpecEntry[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
  disabled?: boolean;
}

export function specKey(entry: SpecEntry): string {
  return `${entry.id}@${entry.version}`;
}

export default function SpecPicker({
  specs,
  selectedKey,
  onSelect,
  disabled,
}: SpecPickerProps) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ fontSize: "0.875rem", color: "#a8b0b8" }}>Spec</span>
      <select
        value={selectedKey ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        disabled={disabled || specs.length === 0}
        style={{
          padding: "0.5rem 0.75rem",
          background: "#1a1d21",
          color: "#e6e8eb",
          border: "1px solid #2a2f35",
          borderRadius: 6,
          fontSize: "0.9375rem",
        }}
      >
        {specs.length === 0 ? (
          <option value="">No specs available</option>
        ) : (
          specs.map((entry) => {
            const key = specKey(entry);
            return (
              <option key={key} value={key}>
                {entry.title} ({entry.id}@{entry.version})
              </option>
            );
          })
        )}
      </select>
    </label>
  );
}
