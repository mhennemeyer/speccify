// Startansicht des Agent-Terminals (Spec 009): Fortsetzen nur mit bekannter,
// vorhandener Sitzung; sonst sichtbar und ausdrücklich wählen. Die native
// Seite baut das Kommando und lehnt ab, was sie nicht genau kann.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  describeSessionRequest,
  hostOf,
  type AgentSessionRecord,
  type SessionRequest,
} from "../lib/agents";

export type SessionState =
  /** Kein Merker oder Shell-only: einfach starten. */
  | { kind: "none" }
  /** Prüfung läuft noch. */
  | { kind: "checking" }
  /** Genau diese Sitzung existiert im Host-Speicher. */
  | { kind: "exact"; id: string }
  /** Merker ohne Identität (Codex, alter Merker) — Auswahl statt Automatik. */
  | { kind: "unknown"; reason: string }
  /** Gemerkte Sitzung ist im Host-Speicher verschwunden. */
  | { kind: "missing"; id: string }
  /** Anderer Host als bei der gemerkten Sitzung. */
  | { kind: "host"; recorded: string }
  /** Freies Kommando: kein automatisches Fortsetzen. */
  | { kind: "free" };

export function useSessionState(record: AgentSessionRecord | null, command: string): SessionState {
  const [state, setState] = useState<SessionState>({ kind: "checking" });
  const host = hostOf(command);
  const recordHost = record?.host ?? "";
  const recordId = record?.id ?? null;
  useEffect(() => {
    let cancelled = false;
    if (!record) {
      setState({ kind: "none" });
      return;
    }
    if (!command.trim()) {
      setState({ kind: "none" });
      return;
    }
    if (!host) {
      setState({ kind: "free" });
      return;
    }
    if (!recordHost) {
      setState({ kind: "unknown", reason: "Aus einer früheren Sitzung ist keine Sitzungs-ID bekannt." });
      return;
    }
    if (recordHost !== host) {
      setState({ kind: "host", recorded: recordHost });
      return;
    }
    if (!recordId) {
      setState({
        kind: "unknown",
        reason: `${recordHost} vergibt beim Start keine wählbare Sitzungs-ID.`,
      });
      return;
    }
    setState({ kind: "checking" });
    void invoke<boolean>("agent_session_check", { host: recordHost, id: recordId })
      .then((exists) => {
        if (cancelled) return;
        setState(exists ? { kind: "exact", id: recordId } : { kind: "missing", id: recordId });
      })
      .catch(() => {
        if (!cancelled) setState({ kind: "missing", id: recordId });
      });
    return () => {
      cancelled = true;
    };
    // `record` object identity changes on every save; its fields drive the check.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [record ? 1 : 0, recordHost, recordId, command, host]);
  return state;
}

export function sessionNotice(state: SessionState): string | null {
  switch (state.kind) {
    case "missing":
      return `Die gemerkte Sitzung ${state.id.slice(0, 8)} wurde im Speicher des Hosts nicht gefunden. Bitte ausdrücklich wählen.`;
    case "host":
      return `Die gemerkte Sitzung gehört zu ${state.recorded}; das Kommando startet jetzt einen anderen Host. Bitte ausdrücklich wählen.`;
    case "unknown":
      return `${state.reason} Fortsetzen nur über die Auswahl des Hosts; „Neueste Sitzung“ ist eine Komfortfunktion, nicht zwingend die gemerkte.`;
    case "free":
      return "Freies Kommando: kein automatisches Fortsetzen. Eine Resume-Option gehört dann ins Kommando selbst.";
    default:
      return null;
  }
}

export default function SessionChoice({
  state,
  command,
  record,
  error,
  onStart,
}: {
  state: SessionState;
  command: string;
  record: AgentSessionRecord | null;
  /** Letzter Startfehler (z. B. Fortsetzen abgelehnt) — sichtbar, nicht „fortgesetzt“. */
  error?: string | null;
  onStart: (request: SessionRequest) => void;
}) {
  const host = hostOf(command);
  const notice = sessionNotice(state);
  const secondary = "rounded bg-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-600";
  const primary = "rounded bg-emerald-700 px-4 py-2 text-sm text-white hover:bg-emerald-600";
  // Nach einem abgelehnten Start stehen alle ausdrücklichen Wege offen.
  const chooser =
    !!error || state.kind === "unknown" || state.kind === "missing" || state.kind === "host";
  return (
    <div className="flex w-full max-w-xs flex-col items-center gap-2" data-session-state={state.kind}>
      {error ? (
        <p className="w-full rounded border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300" role="alert">
          {error}
        </p>
      ) : null}
      {notice ? <p className="text-center text-xs text-amber-300">{notice}</p> : null}
      <div className="flex flex-wrap justify-center gap-2">
        {state.kind === "exact" && host ? (
          <button
            onClick={() => onStart({ mode: "resume", host, id: state.id })}
            className={primary}
            title={describeSessionRequest({ mode: "resume", host, id: state.id }, host)}
          >
            Sitzung fortsetzen
          </button>
        ) : null}
        {chooser && host ? (
          <>
            <button
              onClick={() => onStart({ mode: "pick" })}
              className={primary}
              title={describeSessionRequest({ mode: "pick" }, host)}
            >
              Sitzung auswählen
            </button>
            <button
              onClick={() => onStart({ mode: "latest" })}
              className={secondary}
              title={describeSessionRequest({ mode: "latest" }, host)}
            >
              Neueste Sitzung
            </button>
          </>
        ) : null}
        <button
          onClick={() => onStart({ mode: "new" })}
          className={secondary}
          disabled={state.kind === "checking"}
          title={host ? describeSessionRequest({ mode: "new" }, host) : undefined}
        >
          {state.kind === "checking"
            ? "Sitzung wird geprüft…"
            : record && command.trim()
              ? "Neu starten"
              : "Agent-Terminal starten"}
        </button>
      </div>
    </div>
  );
}
