import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";
import { ErrorBox, LoadingBoundary, useAsync } from "../components/ui";
import { autonomySettings, settingsFields, settingsReferences, settingValue, type SettingField } from "../lib/agentSettings";

interface AgentConfigFile { id: string; host: string; path: string; hint: string; exists: boolean }
const inputClass = "w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm";
const buttonClass = "rounded border border-slate-300 px-3 py-1.5 text-xs disabled:opacity-40";

function Field({ field, value, edit, onChange }: {
  field: SettingField; value: unknown; edit: string | undefined; onChange: (text: string) => void;
}) {
  const key = field.path.join(".");
  const text = edit ?? (value === undefined ? "null" : JSON.stringify(value, null, 2));
  let parsed: unknown; try { parsed = JSON.parse(text); } catch { parsed = undefined; }
  const simple = field.type === "string" && !field.options;
  const numeric = field.type === "integer" || field.type === "number";
  const options = field.type === "boolean" ? [true, false] : field.options;
  const useSelect = options && (text === "null" || options.some(option => JSON.stringify(option) === text));
  return <div className="rounded border border-slate-200 bg-white p-3">
    <div className="mb-1 flex items-start justify-between gap-2">
      <label htmlFor={`setting-${key}`} className="break-all font-mono text-xs font-semibold">{key}</label>
      <button className="shrink-0 text-xs text-blue-700" onClick={() => onChange("null")}>Nicht setzen</button>
    </div>
    {useSelect ? <select id={`setting-${key}`} value={text} className={inputClass} onChange={e => onChange(e.target.value)}>
      <option value="null">Nicht gesetzt · Host-Standard / andere Ebene</option>
      {options.map(option => <option key={JSON.stringify(option)} value={JSON.stringify(option)}>{String(option)}</option>)}
    </select> : simple ? <input id={`setting-${key}`} className={inputClass} value={typeof parsed === "string" ? parsed : ""}
      placeholder="Nicht gesetzt" onChange={e => onChange(JSON.stringify(e.target.value))} />
      : numeric ? <input id={`setting-${key}`} type="number" className={inputClass}
        min={field.minimum} max={field.maximum} step={field.type === "integer" ? 1 : "any"}
        value={typeof parsed === "number" ? parsed : ""} placeholder="Nicht gesetzt"
        onChange={e => onChange(e.target.value ? JSON.stringify(Number(e.target.value)) : "null")} />
      : <textarea id={`setting-${key}`} rows={4}
        spellCheck={false} className={`${inputClass} font-mono text-xs`} value={text} onChange={e => onChange(e.target.value)} />}
    {options && field.type === "json" && <button className="mt-1 text-xs text-blue-700" onClick={() => onChange("{}")}>Komplexen JSON-Wert bearbeiten</button>}
    <p className="mt-2 whitespace-pre-wrap text-xs text-slate-500">{field.help}</p>
    {!simple && !numeric && !useSelect && <p className="mt-1 text-xs text-slate-500">JSON-Wert; null entfernt die Einstellung aus dieser Datei.</p>}
    {numeric && (field.minimum !== undefined || field.maximum !== undefined) && <p className="mt-1 text-xs text-slate-500">Bereich: {field.minimum ?? "offen"} bis {field.maximum ?? "offen"}.</p>}
  </div>;
}

function ConfigEditor({ file, onDirty }: { file: AgentConfigFile; onDirty: (dirty: boolean) => void }) {
  const [content, setContent] = useState("");
  const [original, setOriginal] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [values, setValues] = useState<unknown>({});
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [source, setSource] = useState(false);
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("Berechtigungen und Sandbox");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const fields = useMemo(() => settingsFields(file.id), [file.id]);
  const structured = fields.length > 0;
  const dirty = content !== original || Object.keys(edits).length > 0;
  useEffect(() => { onDirty(dirty); }, [dirty, onDirty]);
  useEffect(() => {
    let disposed = false;
    void invoke<string>("agent_config_read", { id: file.id }).then(async text => {
      if (disposed) return;
      setContent(text); setOriginal(text);
      if (structured) {
        try {
          const parsed = await invoke("agent_config_parse", { id: file.id, content: text });
          if (!disposed) setValues(parsed);
        } catch (e) { if (!disposed) { setError(String(e)); setSource(true); } }
      }
      if (!disposed) setLoaded(true);
    }).catch(e => { if (!disposed) setError(String(e)); });
    return () => { disposed = true; };
  }, [file.id, structured]);

  async function materialize() {
    const changes = Object.entries(edits).map(([key, text]) => {
      try { return { path: key.split("."), value: JSON.parse(text) }; }
      catch { throw new Error(`${key}: ungültiger JSON-Wert`); }
    });
    return changes.length ? invoke<string>("agent_config_patch", { id: file.id, content, changes }) : content;
  }
  async function changeView() {
    setBusy(true); setError("");
    try {
      const next = await materialize();
      if (source) setValues(await invoke("agent_config_parse", { id: file.id, content: next }));
      setContent(next); setEdits({}); setSource(!source);
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  async function save() {
    setBusy(true); setError("");
    try {
      const next = await materialize();
      await invoke("agent_config_write", { id: file.id, content: next, expectedContent: original });
      setContent(next); setOriginal(next); setEdits({});
      if (structured) setValues(await invoke("agent_config_parse", { id: file.id, content: next }));
      setStatus("Gespeichert. Beim nächsten Agent-Start wirksam. Laufende Sitzung bei Bedarf neu starten.");
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  async function reset() {
    setBusy(true);
    setContent(original); setEdits({}); setError(""); setStatus("");
    try { if (structured) setValues(await invoke("agent_config_parse", { id: file.id, content: original })); }
    catch (e) { setError(String(e)); setSource(true); }
    finally { setBusy(false); }
  }
  const shown = fields.filter(field => search
    ? `${field.path.join(".")} ${field.help}`.toLowerCase().includes(search.toLowerCase()) : field.group === group);
  return <div className="flex min-h-0 flex-1 flex-col gap-3" data-update-dirty={dirty}>
    <p className="break-all font-mono text-xs text-slate-500">{file.path}</p>
    <p className="text-xs text-slate-600">Globale Einstellungen für diesen Benutzer und alle Projekte.
      Projektdateien, aktive Profile, Startparameter und verwaltete Regeln können Werte übersteuern.
      Der Agent liest die Datei beim Start; dies ist keine Anzeige der effektiven Sitzungseinstellungen.</p>
    <div className="flex flex-wrap gap-2">
      <button className={buttonClass} disabled={!loaded || busy || !dirty} onClick={() => void save()}>Speichern</button>
      <button className={buttonClass} disabled={!dirty || busy} onClick={() => void reset()}>Änderungen zurücknehmen</button>
      {structured && <button className={buttonClass} disabled={!loaded || busy} onClick={() => void changeView()}>{source ? "Strukturierte Ansicht" : "Quelltext"}</button>}
      {structured && <button className={buttonClass} onClick={() => void openUrl(settingsReferences[file.id])}>Referenz öffnen</button>}
    </div>
    {error && <ErrorBox message={error} />}
    {status && !dirty && <p role="status" className="text-xs text-emerald-700">{status}</p>}
    {!loaded && <p className="text-xs">Datei wird gelesen…</p>}
    {loaded && (source || !structured) ? <textarea aria-label="Agent-Konfiguration Quelltext" spellCheck={false}
      value={content} disabled={busy} onChange={e => { setContent(e.target.value); setStatus(""); }}
      className="min-h-64 flex-1 rounded border border-slate-300 bg-white p-3 font-mono text-xs" />
      : loaded && <fieldset disabled={busy} className="flex min-h-0 flex-1 flex-col gap-3">
        <details className="rounded border border-blue-200 bg-blue-50 p-3 text-xs">
          <summary className="cursor-pointer font-semibold">Empfohlener Ausgangspunkt: Selbstständig arbeiten</summary>
          <p className="my-2">{file.host === "codex"
            ? "on-request + auto_review + workspace-write: Automatische Prüfung geeigneter Freigaben, Änderungen im Arbeitsordner, Netzwerk bleibt separat geregelt. Terminalmeldungen werden aktiviert. Aktuelle Codex-Version nötig. Unter Windows zusätzlich windows.sandbox prüfen und Codex-Sandbox einmalig einrichten."
            : "permissions.defaultMode = auto: Automatische Befehlsprüfung. Konto, Modell und Admin-Regeln müssen Auto erlauben; explizite ask-Regeln können weiter fragen. acceptEdits ist eine Alternative, reduziert aber hauptsächlich Rückfragen bei Dateiänderungen."}</p>
          <p className="my-2">Das Profil verändert nur die unten aufgeführten Werte. Bestehende Regeln und übrige Einstellungen bleiben erhalten. Es wird erst mit Speichern übernommen.</p>
          <pre className="my-2 whitespace-pre-wrap">{JSON.stringify(autonomySettings[file.id], null, 2)}</pre>
          <button className={buttonClass} onClick={() => {
            setEdits(previous => ({ ...previous, ...Object.fromEntries(Object.entries(autonomySettings[file.id]).map(([key, value]) => [key, JSON.stringify(value)])) }));
            setStatus("");
          }}>Profil in Entwurf übernehmen</button>
        </details>
        <input aria-label="Agent-Einstellungen suchen" placeholder="Einstellung oder Hilfetext suchen…" className={inputClass}
          value={search} onChange={e => setSearch(e.target.value)} />
        <div className="flex flex-wrap gap-1">{[...new Set(fields.map(field => field.group))].map(name => <button key={name}
          aria-pressed={!search && group === name} className={`${buttonClass} ${group === name && !search ? "bg-slate-800 text-white" : ""}`}
          onClick={() => { setGroup(name); setSearch(""); }}>{name}</button>)}</div>
        <p className="text-xs text-slate-500">{shown.length} von {fields.length} Einstellungen · Schema-Stand 16.09.2026.
          Hilfe der Referenz teilweise Englisch. Komplexe Werte als JSON; neue oder unbekannte Schlüssel im Quelltext.
          Die installierte CLI kann weniger Optionen unterstützen.</p>
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
          {shown.map(field => <Field key={field.path.join(".")} field={field} value={settingValue(values, field.path)}
            edit={edits[field.path.join(".")]} onChange={text => { setEdits(previous => ({ ...previous, [field.path.join(".")]: text })); setStatus(""); }} />)}
          {!shown.length && <p className="text-sm text-slate-500">Keine passende Einstellung gefunden.</p>}
        </div>
      </fieldset>}
  </div>;
}

export default function AgentsView() {
  const list = useAsync(() => invoke<AgentConfigFile[]>("agent_config_list"), "agent-configs");
  const [selected, setSelected] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [switchTo, setSwitchTo] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const files = list.data ?? [];
  const current = files.find(file => file.id === selected) ?? files.find(file => file.id === "codex-config") ?? files[0];
  return <LoadingBoundary loading={list.loading} error={list.error} label="Agent-Configs suchen…">
    <div className="flex h-full min-h-0 flex-col gap-3">
      <nav className="flex flex-wrap gap-2">{files.map(file => <button key={file.id} className={`${buttonClass} ${file.id === current?.id ? "bg-slate-800 text-white" : ""}`}
        onClick={() => { if (file.id === current?.id) return; if (dirty) setSwitchTo(file.id); else setSelected(file.id); }}>
        {file.host === "codex" ? "Codex" : "Claude"} · {file.id.endsWith("md") ? "Anweisungen" : "Einstellungen"}
      </button>)}<button className={buttonClass} onClick={() => {
        if (dirty && current) setSwitchTo(current.id); else setRevision(value => value + 1);
      }}>Datei neu laden</button></nav>
      {switchTo && <div role="alert" className="rounded border border-amber-300 p-3 text-sm">Ungespeicherte Änderungen verwerfen?
        <button className={`${buttonClass} ml-2`} onClick={() => { setSelected(switchTo); setSwitchTo(null); setDirty(false); setRevision(value => value + 1); }}>Verwerfen und wechseln</button>
        <button className={`${buttonClass} ml-2`} onClick={() => setSwitchTo(null)}>Weiter bearbeiten</button>
      </div>}
      {current && <ConfigEditor key={`${current.id}:${revision}`} file={current} onDirty={setDirty} />}
    </div>
  </LoadingBoundary>;
}
