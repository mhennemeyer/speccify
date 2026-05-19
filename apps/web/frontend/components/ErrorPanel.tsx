"use client";

import { ApiError } from "@/lib/api";

/**
 * Renders structured backend errors with extra UX for `cache_miss` —
 * including the maintainer hint to record the missing cache entry.
 */
export interface ErrorPanelProps {
  error: unknown;
}

function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

export default function ErrorPanel({ error }: ErrorPanelProps) {
  if (!error) return null;

  const isCacheMiss = isApiError(error) && error.errorCode === "cache_miss";
  const headline = isApiError(error)
    ? `${error.errorCode} · ${error.status}`
    : "error";
  const message = error instanceof Error ? error.message : String(error);
  const hint = isApiError(error) ? error.hint : undefined;
  const details = isApiError(error) ? error.details : undefined;

  return (
    <div
      role="alert"
      style={{
        background: isCacheMiss ? "#3a2d10" : "#3a1010",
        border: `1px solid ${isCacheMiss ? "#a16207" : "#b91c1c"}`,
        borderRadius: 6,
        padding: "0.75rem 1rem",
        fontSize: "0.875rem",
        color: "#fef3c7",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{headline}</div>
      <div style={{ color: "#fde68a" }}>{message}</div>
      {hint && (
        <div
          style={{
            marginTop: 8,
            padding: "0.5rem 0.625rem",
            background: "rgba(0,0,0,0.25)",
            borderRadius: 4,
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            fontSize: "0.8125rem",
            whiteSpace: "pre-wrap",
          }}
        >
          {hint}
        </div>
      )}
      {details != null && (
        <pre
          style={{
            marginTop: 8,
            fontSize: "0.75rem",
            color: "#fde68a",
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
          }}
        >
          {typeof details === "string" ? details : JSON.stringify(details, null, 2)}
        </pre>
      )}
    </div>
  );
}
