// Auftrags-Vorschau (Spec 011): zeigt, was der Agent bekommt, liest die Datei
// beim Öffnen und noch einmal vor der Zustellung, meldet Abweichungen und das
// Zustellergebnis. Kein Auftrag ohne Klick; Enter im Terminal bleibt beim Menschen.

import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  buildHandover,
  guardPlaybookHandover,
  copyHandover,
  deliverToTerminal,
  kindsFor,
  KIND_LABELS,
  terminalIsFresh,
  terminalReady,
  type HandoverItem,
  type HandoverKind,
} from "../lib/handover";
import { InspectorButton } from "../lib/panels";
import { t } from "../i18n";

export function HandoverButton({ project, item, known }: { project: string; item: HandoverItem; known?: string | null }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <InspectorButton title={t("Auftrag mit Projekt, Pfad und Absicht ans Agent-Terminal übergeben oder kopieren")} onClick={() => setOpen(true)}>
        {t("Auftrag…")}
      </InspectorButton>
      {open ? <HandoverSheet project={project} item={item} known={known ?? null} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

export default function HandoverSheet({
  project,
  item,
  known,
  onClose,
}: {
  project: string;
  item: HandoverItem;
  /** Inhalt, wie ihn die Ansicht zuletzt kannte — für den Abweichungshinweis. */
  known: string | null;
  onClose: () => void;
}) {
  const [kind, setKind] = useState<HandoverKind>(() => kindsFor(item.type, known)[0]);
  const [content, setContent] = useState<string | null>(null);
  const kinds = kindsFor(item.type, content);
  const selectedKind = kinds.includes(kind) ? kind : kinds[0];
  const [readError, setReadError] = useState<string | null>(null);
  const [edited, setEdited] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [tone, setTone] = useState<"ok" | "warn" | "error">("ok");
  const [ready, setReady] = useState(terminalReady());
  const [fresh, setFresh] = useState(terminalIsFresh());

  const read = async (): Promise<string | null> => {
    try {
      const text = await invoke<string>("project_read_file", { project, file: item.path });
      setContent(text);
      setReadError(null);
      return text;
    } catch (error) {
      setReadError(String(error));
      return null;
    }
  };
  useEffect(() => {
    void read();
    const timer = setInterval(() => {
      setReady(terminalReady());
      setFresh(terminalIsFresh());
    }, 1000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.path]);

  const stripFrontMatter = (text: string) => {
    if (!text.startsWith("---")) return text;
    const end = text.indexOf("\n---", 3);
    return end === -1 ? text : text.slice(text.indexOf("\n", end + 1) + 1);
  };
  const changed =
    known !== null &&
    content !== null &&
    (item.type === "playbook" ? known !== content : stripFrontMatter(known).trimEnd() !== stripFrontMatter(content).trimEnd());
  const preview = useMemo(
    () => (content !== null ? edited !== null ? guardPlaybookHandover(item, content, edited) : buildHandover(project, item, selectedKind, content) : ""),
    [edited, content, project, item, selectedKind],
  );

  const deliver = async () => {
    // Vor der Übergabe die aktuelle Datei lesen — nie einen alten Stand zustellen.
    const fresh = await read();
    if (fresh === null) {
      setTone("error");
      setResult(t("Datei konnte nicht gelesen werden — nichts zugestellt."));
      return;
    }
    const text = edited !== null ? guardPlaybookHandover(item, fresh, edited) : buildHandover(project, item, selectedKind, fresh);
    const outcome = await deliverToTerminal(text);
    if (outcome.status === "delivered") {
      setTone("ok");
      setResult(t("Eingefügt — im Terminal mit Enter absenden."));
    } else if (outcome.status === "no-terminal") {
      setTone("warn");
      setResult(t("Kein Agent-Terminal bereit — Auftrag kopieren oder Terminal starten."));
    } else {
      setTone("error");
      setResult(`Zustellung fehlgeschlagen: ${outcome.message}`);
    }
  };

  const copy = async () => {
    const fresh = await read();
    if (fresh === null) return;
    const text = edited !== null ? guardPlaybookHandover(item, fresh, edited) : buildHandover(project, item, selectedKind, fresh);
    await copyHandover(text);
    setTone("ok");
    setResult(t("In die Zwischenablage kopiert."));
  };

  const button = "rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50";
  const quiet = "rounded border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100";
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20" onClick={onClose}>
      <div role="dialog" aria-label="Auftrag" onClick={(event) => event.stopPropagation()} className="flex max-h-[85vh] w-[720px] max-w-[95vw] flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-xl">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800">{t("Auftrag an den Agenten")}</h2>
          <span className="truncate font-mono text-[11px] text-slate-500" title={item.path}>{item.path}</span>
          <button onClick={onClose} className="ml-auto text-xs text-slate-400 hover:text-slate-700">{t("Schließen")}</button>
        </div>
        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <span>Absicht:</span>
          {kinds.map((option) => (
            <button
              key={option}
              onClick={() => { setKind(option); setEdited(null); }}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${selectedKind === option ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
            >
              {t(KIND_LABELS[option])}
            </button>
          ))}
          <span className="ml-auto" data-terminal-ready={ready}>{ready ? t("Agent-Terminal bereit") : t("kein Agent-Terminal")}</span>
        </div>
        {ready && fresh ? (
          <p className="mb-2 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800" role="status" data-fresh-terminal>
            {t("Das Terminal ist gerade erst gestartet. Warte, bis der Agent seine Eingabezeile zeigt — Claude fragt bei neuen Ordnern zuerst „Trust this folder?“ — sonst geht der eingefügte Text verloren.")}
          </p>
        ) : null}
        {changed ? (
          <p className="mb-2 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800" role="status">
            {t("Die Datei hat sich seit der Auswahl geändert — die Vorschau zeigt den aktuellen Inhalt.")}
          </p>
        ) : null}
        {readError ? <p className="mb-2 text-xs text-red-700">{readError}</p> : null}
        <textarea
          aria-label="Auftragstext"
          value={preview}
          onChange={(event) => setEdited(event.target.value)}
          spellCheck={false}
          className="min-h-0 flex-1 resize-none rounded border border-slate-300 bg-slate-50 p-2 font-mono text-[11px] leading-snug text-slate-800"
          style={{ minHeight: 240 }}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button className={button} disabled={content === null} onClick={() => void deliver()}>{t("Ins Terminal einfügen")}</button>
          <button className={quiet} onClick={() => void copy()}>{t("Kopieren")}</button>
          {!ready ? (
            <button className={quiet} onClick={() => window.dispatchEvent(new CustomEvent("speccify:show-terminal"))}>{t("Terminal starten")}</button>
          ) : null}
          {edited !== null ? <button className={quiet} onClick={() => setEdited(null)}>{t("Vorlage wiederherstellen")}</button> : null}
          {result ? (
            <span role="status" className={`text-xs ${tone === "ok" ? "text-emerald-700" : tone === "warn" ? "text-amber-700" : "text-red-700"}`}>{result}</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
