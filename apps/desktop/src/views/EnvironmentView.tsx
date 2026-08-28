// Umgebung: Doctor-Karten, Python-Versionen (via uv) und die mitgelieferte
// Python-Engine der App (R5.2) — deren venv wird hier installiert/erneuert.

import { useEffect, useRef, useState } from "react";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import {
  ENGINE_LOG_ID,
  fetchDoctor,
  fetchEngineStatus,
  fetchPythons,
  fetchUpdaterStatus,
  installEngine,
  installPython,
  type DoctorCheck,
  type EngineStatus,
  type PythonsInfo,
  type UpdaterStatus,
} from "../lib/system";
import {
  ActionButton,
  ErrorBox,
  LoadingBoundary,
  Spinner,
  useAsync,
} from "../components/ui";

interface EnvData {
  checks: DoctorCheck[];
  pythons: PythonsInfo;
  engine: EngineStatus;
  updater: UpdaterStatus;
}

export default function EnvironmentView() {
  const { data, loading, refreshing, error, reload } = useAsync<EnvData>(async () => {
    const [doctor, pythons, engine, updater] = await Promise.all([
      fetchDoctor(),
      fetchPythons(),
      fetchEngineStatus(),
      fetchUpdaterStatus(),
    ]);
    return { checks: doctor.checks, pythons, engine, updater };
  }, "environment");

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <ActionButton
          onClick={reload}
          className="bg-slate-800 text-white hover:bg-slate-700"
        >
          Neu prüfen
        </ActionButton>
        {refreshing && <Spinner />}
      </div>

      <LoadingBoundary loading={loading} error={error} label="Umgebung wird geprüft…">
        {data && (
          <>
            <UpdateCard updater={data.updater} />
            <EngineCard engine={data.engine} onChanged={reload} />
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {data.checks.map((c) =>
              c.binary === "python3" ? (
                <PythonCard
                  key={c.binary}
                  check={c}
                  pythons={data.pythons}
                  onInstalled={reload}
                />
              ) : (
                <CheckCard key={c.binary} check={c} />
              ),
            )}
          </div>
          </>
        )}
      </LoadingBoundary>
    </div>
  );
}

/**
 * App-Version + Update-Suche (R5.4). Der Updater lädt erst, wenn er
 * konfiguriert ist — der Import passiert deshalb dynamisch, sonst zöge ein
 * Build ohne Signaturschlüssel das Plugin unnötig ins Bundle.
 */
function UpdateCard({ updater }: { updater: UpdaterStatus }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const check = async () => {
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      const { check: checkUpdate } = await import("@tauri-apps/plugin-updater");
      const update = await checkUpdate();
      if (!update) {
        setMessage("Kein Update verfügbar — die App ist aktuell.");
        return;
      }
      setMessage(`Version ${update.version} wird geladen …`);
      await update.downloadAndInstall();
      setMessage(
        `Version ${update.version} installiert — Speccify beenden und neu starten.`,
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="mb-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-slate-900">Speccify</h3>
        <span className="text-sm text-slate-500">Version {updater.current_version}</span>
      </div>
      {updater.configured ? (
        <div className="mt-3 flex items-center gap-3 border-t border-slate-100 pt-3">
          <ActionButton
            onClick={check}
            className="bg-slate-800 text-white hover:bg-slate-700"
          >
            Nach Updates suchen
          </ActionButton>
          {busy && <Spinner />}
          {message && <span className="text-xs text-slate-500">{message}</span>}
        </div>
      ) : (
        <p className="mt-2 text-xs text-slate-500">
          Automatische Updates sind in diesem Build nicht eingerichtet (kein
          Signaturschlüssel hinterlegt) — siehe docs/release.md.
        </p>
      )}
      {error && (
        <div className="mt-2">
          <ErrorBox message={error} />
        </div>
      )}
    </article>
  );
}

/** Mitgelieferte Python-Engine (R5.2): Status + Installation mit Live-Log. */
function EngineCard({
  engine,
  onChanged,
}: {
  engine: EngineStatus;
  onChanged: () => Promise<unknown>;
}) {
  const [busy, setBusy] = useState(false);
  const [installError, setInstallError] = useState<string | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const unlistenRef = useRef<UnlistenFn | null>(null);

  useEffect(() => {
    void listen<{ id: string; line: string }>("proc-log", (event) => {
      if (event.payload.id !== ENGINE_LOG_ID) return;
      setLog((current) => [...current.slice(-200), event.payload.line]);
    }).then((unlisten) => {
      unlistenRef.current = unlisten;
    });
    return () => {
      unlistenRef.current?.();
    };
  }, []);

  const install = async () => {
    setInstallError(null);
    setLog([]);
    setBusy(true);
    try {
      await installEngine();
      await onChanged();
    } catch (e) {
      setInstallError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const state = engine.ready
    ? { icon: "✅", text: "einsatzbereit", tone: "border-slate-200 bg-white" }
    : engine.needs_update
      ? {
          icon: "⚠️",
          text: "veraltet (App wurde aktualisiert)",
          tone: "border-amber-200 bg-amber-50",
        }
      : { icon: "❌", text: "nicht installiert", tone: "border-amber-200 bg-amber-50" };

  return (
    <article className={`mb-3 rounded-lg border p-4 ${state.tone}`}>
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-slate-900">
          {state.icon} Python-Engine (Spec-Engine)
        </h3>
        <span className="text-sm text-slate-500">{state.text}</span>
      </div>
      <p className="mt-1 truncate text-xs text-slate-400">{engine.venv_dir}</p>

      {!engine.payload_found ? (
        <p className="mt-2 text-sm text-amber-800">
          Kein Engine-Payload im App-Bundle — vor dem Build einmal{" "}
          <code className="rounded bg-amber-100 px-1">
            ./scripts/build_engine_payload.sh
          </code>{" "}
          ausführen.
        </p>
      ) : (
        <div className="mt-3 flex items-center gap-3 border-t border-slate-100 pt-3">
          {engine.uv_source === "missing" ? (
            <span className="text-xs text-amber-700">
              braucht uv (<code>brew install uv</code>)
            </span>
          ) : (
            <ActionButton
              onClick={install}
              className="bg-slate-800 text-white hover:bg-slate-700"
              title="uv venv + uv pip install aus dem mitgelieferten Payload"
            >
              {engine.ready
                ? "Neu installieren"
                : engine.needs_update
                  ? "Aktualisieren"
                  : "Engine installieren"}
            </ActionButton>
          )}
          {busy && <Spinner />}
          <span className="text-xs text-slate-500">
            Python {engine.python_version ?? "?"} · erste Installation lädt einmalig
            aus dem Netz
          </span>
        </div>
      )}

      {log.length > 0 && (
        <pre className="mt-3 max-h-48 overflow-auto rounded bg-slate-900 p-2 text-xs text-slate-100">
          {log.join("\n")}
        </pre>
      )}
      {installError && (
        <div className="mt-2">
          <ErrorBox message={installError} />
        </div>
      )}
    </article>
  );
}

function CheckCard({ check: c }: { check: DoctorCheck }) {
  return (
    <article
      className={`rounded-lg border p-4 ${
        c.found ? "border-slate-200 bg-white" : "border-amber-200 bg-amber-50"
      }`}
    >
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-slate-900">
          {c.found ? "✅" : "❌"} {c.name}
        </h3>
        {c.version && <span className="text-sm text-slate-500">{c.version}</span>}
      </div>
      {c.found ? (
        <div className="mt-1 space-y-0.5">
          <p className="truncate text-xs text-slate-400">{c.path}</p>
          {c.candidates.slice(1).map((cand) => (
            <p key={cand.path} className="truncate text-xs text-slate-400">
              <span className="text-slate-500">weitere: {cand.version ?? "?"}</span>{" "}
              {cand.path}
            </p>
          ))}
        </div>
      ) : (
        <p className="mt-1 flex items-center gap-2 text-sm text-amber-800">
          <span>
            Installieren: <code className="rounded bg-amber-100 px-1">{c.hint}</code>
          </span>
          <button
            onClick={() => navigator.clipboard.writeText(c.hint)}
            className="shrink-0 rounded bg-amber-200 px-2 py-0.5 text-xs hover:bg-amber-300"
            title="Install-Befehl kopieren"
          >
            Kopieren
          </button>
        </p>
      )}
    </article>
  );
}

/** Python-Karte: alle Installationen + weitere Versionen via uv installieren. */
function PythonCard({
  check,
  pythons,
  onInstalled,
}: {
  check: DoctorCheck;
  pythons: PythonsInfo;
  onInstalled: () => Promise<unknown>;
}) {
  const [selected, setSelected] = useState(pythons.available[0] ?? "");
  const [installError, setInstallError] = useState<string | null>(null);

  const install = async () => {
    setInstallError(null);
    try {
      await installPython(selected);
      await onInstalled();
    } catch (e) {
      setInstallError(String(e));
    }
  };

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-slate-900">
          {check.found ? "✅" : "❌"} {check.name}
        </h3>
        {check.version && (
          <span className="text-sm text-slate-500">{check.version}</span>
        )}
      </div>
      <div className="mt-1 space-y-0.5">
        {pythons.installed.map((p) => (
          <p key={p.path} className="truncate text-xs text-slate-400">
            <span className="text-slate-500">{p.version ?? "?"}</span> {p.path}
          </p>
        ))}
      </div>

      {pythons.available.length > 0 && (
        <div className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-3">
          <label className="text-sm text-slate-600">Weitere Version:</label>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1 text-sm"
          >
            {pythons.available.map((v) => (
              <option key={v} value={v}>
                Python {v}
              </option>
            ))}
          </select>
          {pythons.uv ? (
            <ActionButton
              onClick={install}
              className="bg-slate-800 text-white hover:bg-slate-700"
              title={`uv python install ${selected}`}
            >
              Installieren
            </ActionButton>
          ) : (
            <span className="text-xs text-amber-700">
              braucht uv (<code>brew install uv</code>)
            </span>
          )}
        </div>
      )}
      {installError && (
        <div className="mt-2">
          <ErrorBox message={installError} />
        </div>
      )}
    </article>
  );
}
