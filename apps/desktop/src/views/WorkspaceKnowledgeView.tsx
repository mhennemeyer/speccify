import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ErrorBox } from "../components/ui";
import { copyHandover, deliverToTerminal } from "../lib/handover";
import { mcpConnectionPrompt, type KnowledgeCatalog, type KnowledgeEntry, type KnowledgeKind } from "../lib/workspaceKnowledge";
import { t } from "../i18n";

const labels = { skills: "Skills", tools: "Tools", mcps: "MCPs", playbooks: "Playbooks" };
const statuses: Record<string, string> = { active: "Aktiv", draft: "Draft", invalid: "Status prüfen", readable: "Lesbar", contract: "Tool-Vertrag", disabled: "Im Host deaktiviert", "host-unconfirmed": "Host-Anbindung ungeprüft" };

export default function WorkspaceKnowledgeView({ workspaceId, root, kind, refresh, onSelect, onManage, onSnapshot }: {
  workspaceId: string; root: string; kind: KnowledgeKind; refresh: number;
  onSelect: (entry: KnowledgeEntry) => void; onManage: (source: string) => void;
  onSnapshot: (snapshot: KnowledgeCatalog | null) => void;
}) {
  const storage = `speccify.workspace.knowledge:${workspaceId}:${kind}`;
  const read = () => { try { return JSON.parse(localStorage.getItem(storage) ?? "{}"); } catch { return {}; } };
  const [search, setSearch] = useState(() => read().search ?? "");
  const [source, setSource] = useState(() => read().source ?? "");
  const [status, setStatus] = useState(() => read().status ?? "");
  const [selected, setSelected] = useState<string>(() => read().selected ?? "");
  const [target, setTarget] = useState("");
  const [snapshot, setSnapshot] = useState<KnowledgeCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const restored = useRef(false);
  const callbacks = useRef({ onSelect, onSnapshot }); callbacks.current = { onSelect, onSnapshot };
  useEffect(() => { try { localStorage.setItem(storage, JSON.stringify({ search, source, status, selected })); } catch { /* Session state remains. */ } }, [storage, search, source, status, selected]);
  useEffect(() => {
    let stopped = false;
    void invoke<KnowledgeCatalog>("workspace_knowledge", { workspaceId }).then(value => {
      if (stopped) return;
      setSnapshot(value); setError(null); callbacks.current.onSnapshot(value);
      if (!restored.current) { const item = value.entries.find(entry => entry.key === selected && entry.kind === kind); if (item) callbacks.current.onSelect(item); restored.current = true; }
    }).catch(e => { if (!stopped) { setError(String(e)); setSnapshot(null); callbacks.current.onSnapshot(null); } });
    return () => { stopped = true; };
  }, [workspaceId, refresh, reload]);
  const entries = snapshot?.entries.filter(entry => entry.kind === kind) ?? [];
  const current = entries.find(entry => entry.key === selected);
  const query = search.toLocaleLowerCase();
  const visible = entries.filter(entry => (!source || entry.worktree_id === source) && (!status || entry.status === status) && [entry.title, entry.name, entry.source, entry.file, entry.host ?? ""].some(value => value.toLocaleLowerCase().includes(query)));
  return <section aria-label={t("Gemeinsame {kind}", { kind: labels[kind] })} className="space-y-2 py-2 text-xs">
    <input aria-label={t("{kind} im Workspace suchen", { kind: labels[kind] })} placeholder={t("{kind} suchen…", { kind: labels[kind] })} value={search} onChange={e => setSearch(e.target.value)} className="w-full rounded border p-2" />
    <select aria-label={t("Wissensquelle filtern")} className="w-full rounded border bg-white p-1" value={source} onChange={e => setSource(e.target.value)}><option value="">{t("Alle Quellen")}</option>{snapshot?.sources.map(source => <option key={source.id} value={source.id}>{source.name}{source.available ? "" : t(" · nicht verfügbar")}</option>)}</select>
    {kind === "playbooks" && <select aria-label="Workspace-Playbook-Status" className="w-full rounded border bg-white p-1" value={status} onChange={e => setStatus(e.target.value)}><option value="">{t("Alle Status")}</option>{["active", "draft", "invalid"].map(value => <option key={value} value={value}>{statuses[value]}</option>)}</select>}
    <div className="flex justify-between"><span>{visible.length} von {entries.length}</span><button onClick={() => setReload(value => value + 1)}>{t("Liste aktualisieren")}</button></div>
    {error && <ErrorBox message={error} />}
    {snapshot?.warnings.map((warning, index) => <p role="status" key={index}>{warning}</p>)}
    {snapshot?.sources.filter(source => source.errors.length || !source.available).map(source => <p role="status" key={source.id}>{source.name}: {source.errors.join(" · ") || t("Nicht verfügbar")}</p>)}
    <div aria-label={t("{kind} aller Quellen", { kind: labels[kind] })} className="space-y-1">
      {visible.map(entry => <button key={entry.key} data-knowledge-key={entry.key} aria-pressed={selected === entry.key} onClick={() => { setSelected(entry.key); onSelect(entry); }} data-tone="violet" className={`block w-full rounded p-2 text-left ${selected === entry.key ? "tone-surface" : "hover:bg-slate-100"}`}>
        <strong className="block">{entry.title}</strong><span className="block break-all">{entry.source} · {entry.host ? `${entry.host} · ` : ""}{t(statuses[entry.status] ?? entry.status)}</span>
      </button>)}
    </div>
    {selected && !current && snapshot && <p role="status">{t("Ausgewählter Eintrag nicht mehr verfügbar. Keine Aktion auf veralteter Quelle ausführen.")}</p>}
    {current && kind === "mcps" && <div className="space-y-1 rounded border p-2">
      <p>{t("Diese Definition ist im Root-Host noch nicht bestätigt. Die Listenanzeige startet keinen Server.")}</p>
      <button onClick={() => void copyHandover(mcpConnectionPrompt(current, root)).then(() => setNotice(t("Anbindungsauftrag kopiert.")))}>{t("Anbindungsauftrag kopieren")}</button>
      <button onClick={() => void deliverToTerminal(mcpConnectionPrompt(current, root)).then(result => setNotice(result.status === "delivered" ? t("Im Root-Terminal eingefügt; Enter bestätigt den Auftrag.") : t("Root-Terminal zuerst starten.")))}>{t("Anbindung im Root-Terminal prüfen…")}</button>
    </div>}
    {notice && <p role="status">{notice}</p>}
    <div className="space-y-1 border-t pt-2">
      <label>Speicher-/Importziel<select aria-label={t("Wissensziel wählen")} className="block w-full rounded border bg-white p-1" value={target} onChange={e => setTarget(e.target.value)}><option value="">{t("Quelle wählen…")}</option>{snapshot?.sources.filter(source => source.available).map(source => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label>
      <button disabled={!target} onClick={() => onManage(target)} className="rounded border px-2 py-1 disabled:opacity-40">{kind === "skills" ? t("Quellen durchsuchen / importieren") : kind === "playbooks" ? t("Playbook hier anlegen") : t("Im gewählten Ziel verwalten")}</button>
    </div>
  </section>;
}
