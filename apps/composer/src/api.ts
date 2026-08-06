// HTTP client for the Speccify backend. Every viewer action exists as an
// endpoint, so agents can do the same thing headlessly.

import type { PlaybookDetail, PlaybookSummary } from "./types";

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

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
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
