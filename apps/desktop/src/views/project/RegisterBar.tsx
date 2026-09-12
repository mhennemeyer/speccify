// Gemeinsames Spec-Register (Spec 028): Zustand des Branch `specs` als
// Worktree unter `.agent/specs`, Einrichten per Knopf (nie automatisch,
// weil Git-Branches und .gitignore geändert werden), Sync-Stand und
// Konfliktentscheidung. Die native Seite synchronisiert von selbst; hier
// wird nur gezeigt und entschieden.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { trackActivity } from "../../lib/activity";

export interface RegisterConflict {
  file: string;
  spec_id: string;
  team: string;
  mine: string;
}

export interface RegisterStatus {
  mode: "none" | "migratable" | "detached" | "blocked" | "mounted";
  branch: string;
  remote: boolean;
  code_branch: string | null;
  tracked_in_code: boolean;
  ahead: number;
  behind: number;
  unsent: number;
  rebasing: boolean;
  conflicts: RegisterConflict[];
  last_sync: string | null;
  last_error: string | null;
  reason: string | null;
}

export default function RegisterBar({
  project,
  onStatus,
}: {
  project: string;
  /** Konflikt-Specs u. a. fürs Board. */
  onStatus?: (status: RegisterStatus) => void;
}) {
  const [status, setStatus] = useState<RegisterStatus | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const apply = (next: RegisterStatus) => {
    setStatus(next);
    onStatus?.(next);
  };

  useEffect(() => {
    let disposed = false;
    void invoke<RegisterStatus>("project_register_status", { project })
      .then((next) => {
        if (!disposed) apply(next);
      })
      .catch((e) => {
        if (!disposed) setError(String(e));
      });
    const unlisten = listen<{ project: string; status: RegisterStatus }>("register-changed", (event) => {
      if (event.payload.project === project) apply(event.payload.status);
    });
    return () => {
      disposed = true;
      void unlisten.then((dispose) => dispose());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  const run = async (label: string, command: string, args: Record<string, unknown> = {}) => {
    setBusy(label);
    setError(null);
    try {
      const next = await trackActivity("setup", label, () =>
        invoke<RegisterStatus>(command, { project, ...args }),
      );
      apply(next);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  if (!status || status.mode === "none") return null;

  const button = "rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50";
  const quiet = "rounded border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50";

  if (status.mode === "migratable" || status.mode === "detached") {
    return (
      <div className="mb-3 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-xs text-sky-900" data-register={status.mode}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-semibold">
              {status.mode === "migratable"
                ? "Specs als gemeinsames Team-Register führen?"
                : "Team-Register vorhanden, noch nicht eingehängt."}
            </p>
            <p className="mt-1">{status.reason}</p>
            {confirming && status.mode === "migratable" ? (
              <p className="mt-1 text-sky-800">
                Das legt den Branch <code>specs</code> mit dem heutigen Stand von <code>.agent/specs</code> an,
                entfernt den Ordner aus <code>{status.code_branch ?? "main"}</code>, trägt ihn in{" "}
                <code>.gitignore</code> ein, committet das und pusht <code>specs</code> und{" "}
                <code>{status.code_branch ?? "main"}</code>. Andere Branches, die <code>.agent/specs</code> noch
                tracken, vorher auf main rebasen.
              </p>
            ) : null}
            {error ? <p className="mt-1 text-red-700">{error}</p> : null}
          </div>
          <div className="flex shrink-0 gap-2">
            {status.mode === "migratable" && !confirming ? (
              <button className={button} onClick={() => setConfirming(true)}>
                Register einrichten…
              </button>
            ) : (
              <button
                className={button}
                disabled={busy !== null}
                onClick={() => void run(status.mode === "migratable" ? "Spec-Register anlegen" : "Spec-Register einhängen", "project_register_setup")}
              >
                {busy ? "Läuft…" : status.mode === "migratable" ? "Jetzt einrichten" : "Einhängen"}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (status.mode === "blocked") {
    return (
      <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-900" data-register="blocked">
        <p className="font-semibold">Spec-Register blockiert.</p>
        <p className="mt-1">{status.reason}</p>
      </div>
    );
  }

  const parts: string[] = [];
  if (status.rebasing) parts.push(`Konflikt in ${status.conflicts.length} Datei${status.conflicts.length === 1 ? "" : "en"}`);
  else if (status.unsent > 0) parts.push(`${status.unsent} nicht gesendet`);
  if (status.ahead > 0) parts.push(`${status.ahead} zu pushen`);
  if (status.behind > 0) parts.push(`${status.behind} neu vom Team`);
  if (parts.length === 0) parts.push("aktuell");

  return (
    <div className="mb-3 text-xs" data-register="mounted" data-register-state={status.rebasing ? "conflict" : "ok"}>
      <div className="flex flex-wrap items-center gap-2 text-slate-600">
        <span className="font-semibold text-slate-700">Register <code>{status.branch}</code></span>
        <span aria-label="Register-Stand">· {parts.join(" · ")}</span>
        {status.last_sync ? <span className="text-slate-400" title={status.last_sync}>· Sync {status.last_sync.slice(11, 16)} UTC</span> : null}
        {status.last_error ? <span className="text-red-700">· {status.last_error}</span> : null}
        {status.reason && !status.rebasing ? <span className="text-amber-700">· {status.reason}</span> : null}
        <button className={quiet} disabled={busy !== null} onClick={() => void run("Spec-Register synchronisieren", "project_register_sync")}>
          {busy ? "Läuft…" : "Sync"}
        </button>
        {error ? <span className="text-red-700">{error}</span> : null}
      </div>
      {status.rebasing ? (
        <div className="mt-2 space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900" role="region" aria-label="Register-Konflikte">
          <p className="font-semibold">
            {status.reason ?? "Konflikt: dieselben Zeilen wurden im Team und hier geändert."} Nichts geht verloren; bis zur Entscheidung wird nicht synchronisiert.
          </p>
          {status.conflicts.map((conflict) => (
            <div key={conflict.file} className="rounded border border-amber-200 bg-white p-2" data-register-conflict={conflict.spec_id}>
              <p className="mb-1 font-mono text-[11px] text-slate-600">{conflict.file}</p>
              <div className="grid gap-2 md:grid-cols-2">
                <div>
                  <p className="mb-1 font-semibold">Team (origin/{status.branch})</p>
                  <pre className="max-h-48 overflow-auto rounded bg-slate-50 p-2 font-mono text-[11px] text-slate-700">{conflict.team}</pre>
                </div>
                <div>
                  <p className="mb-1 font-semibold">Meine Fassung</p>
                  <pre className="max-h-48 overflow-auto rounded bg-slate-50 p-2 font-mono text-[11px] text-slate-700">{conflict.mine}</pre>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <button className={button} disabled={busy !== null} onClick={() => void run("Konflikt: Team-Fassung", "project_register_resolve", { file: conflict.file, choice: "team" })}>
                  Team-Fassung übernehmen
                </button>
                <button className={button} disabled={busy !== null} onClick={() => void run("Konflikt: eigene Fassung", "project_register_resolve", { file: conflict.file, choice: "mine" })}>
                  Meine Fassung behalten
                </button>
                <button className={quiet} disabled={busy !== null} title="Die Datei wurde im Editor bereinigt (keine Konfliktmarker mehr)." onClick={() => void run("Konflikt: bearbeitet", "project_register_resolve", { file: conflict.file, choice: "edited" })}>
                  Bearbeitet — als gelöst markieren
                </button>
              </div>
            </div>
          ))}
          <button className={quiet} disabled={busy !== null} onClick={() => void run("Konflikt: Rebase abbrechen", "project_register_abort")}>
            Abbrechen — eigenen Stand behalten, später erneut
          </button>
        </div>
      ) : null}
    </div>
  );
}
