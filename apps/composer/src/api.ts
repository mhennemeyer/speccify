// HTTP-Client für das Composer-Backend. Alle Composer-Aktionen laufen über
// diese Endpoints — dieselbe API ist auch headless (Agent/CLI) nutzbar.
// API-Base-Auflösung: `window.__SPECCIFY_API__` (Laufzeit, z. B. von einer
// Shell injiziert) > `VITE_API_BASE` (Build-Zeit) > "" (same-origin — der
// Normalfall im Desktop-Composer-Fenster, das die SPA unter /ui vom
// speccify-web-backend lädt, und im Vite-Dev via Proxy).

import type { MockBundle, SpecDetail, SpecSummary, ValidationIssue } from "./types";

declare global {
  interface Window {
    __SPECCIFY_API__?: string;
  }
}

const BASE: string =
  window.__SPECCIFY_API__ ?? (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = JSON.stringify(body.detail ?? body);
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function listSpecs(): Promise<SpecSummary[]> {
  const body = await request<{ specs: SpecSummary[] }>("/api/v1/specs");
  return body.specs;
}

export async function getSpecDetail(specId: string, version?: string): Promise<SpecDetail> {
  const path = specId.replace(/^@/, "");
  const query = version ? `?version=${encodeURIComponent(version)}` : "";
  return request<SpecDetail>(`/api/v1/specs/${path}${query}`);
}

export async function validateSpec(
  specYaml: string,
): Promise<{ ok: boolean; issues: ValidationIssue[] }> {
  return request("/api/v1/validate", {
    method: "POST",
    body: JSON.stringify({ spec_yaml: specYaml }),
  });
}

/** Mock-Closure des (ungespeicherten) Dokuments — die Dateien, die der Canvas rendert. */
export async function mockDraft(specYaml: string): Promise<MockBundle> {
  return request("/api/v1/mock/draft", {
    method: "POST",
    body: JSON.stringify({ spec_yaml: specYaml }),
  });
}

export async function saveSpec(
  specYaml: string,
): Promise<{ id: string; version: string; path: string }> {
  return request("/api/v1/specs", {
    method: "POST",
    body: JSON.stringify({ spec_yaml: specYaml }),
  });
}
