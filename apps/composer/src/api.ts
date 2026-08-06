// HTTP client for the Speccify backend. Every viewer action exists as an
// endpoint, so agents can do the same thing headlessly.

import type { IndexHit, PlaybookDetail, PlaybookSummary } from "./types";

declare global {
  interface Window {
    __SPECCIFY_API__?: string;
  }
}

const BASE: string =
  window.__SPECCIFY_API__ ?? (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = JSON.stringify(body.detail ?? body);
    } catch {
      /* keep the status text */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export async function listPlaybooks(): Promise<PlaybookSummary[]> {
  const body = await request<{ playbooks: PlaybookSummary[] }>("/api/v1/playbooks");
  return body.playbooks;
}

export async function getPlaybook(source: string): Promise<PlaybookDetail> {
  return request<PlaybookDetail>(`/api/v1/playbook?source=${encodeURIComponent(source)}`);
}

export async function getAsset(
  source: string,
  path: string,
): Promise<{ path: string; encoding: string; content: string }> {
  return request(
    `/api/v1/playbook/asset?source=${encodeURIComponent(source)}&path=${encodeURIComponent(path)}`,
  );
}

/** Discovery: find playbooks that are not in the local library. */
export async function searchIndex(query: string): Promise<IndexHit[]> {
  const body = await request<{ hits: IndexHit[] }>(`/api/v1/index?q=${encodeURIComponent(query)}`);
  return body.hits;
}

/** Tell the backend what the user selected — this is what the agent reads. */
export async function pushSelection(selection: {
  source: string;
  kind: string;
  step_id?: string;
  source_id?: string;
  asset_path?: string;
}): Promise<void> {
  await request("/api/v1/selection", {
    method: "PUT",
    body: JSON.stringify(selection),
  });
}

export interface Proposal {
  source: string;
  playbook_yaml: string;
  rationale: string;
}

/** A change an agent suggested; empty object when there is none. */
export async function getProposal(): Promise<Proposal | null> {
  const body = await request<{ proposal: Proposal | Record<string, never> }>(
    "/api/v1/proposal",
  );
  return "playbook_yaml" in body.proposal ? (body.proposal as Proposal) : null;
}

export async function applyProposal(): Promise<{ path: string }> {
  return request("/api/v1/proposal/apply", { method: "POST" });
}

export async function discardProposal(): Promise<void> {
  await request("/api/v1/proposal", { method: "DELETE" });
}
