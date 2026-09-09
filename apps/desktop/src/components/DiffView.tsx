// Unified-Diff-Ansicht mit Hunks (Plan ide-im-projektfenster.md, I3):
// je Hunk eine Kopfzeile mit optionalen Aktionen (stagen / zurücknehmen).

import type { ReactNode } from "react";
import { parseDiff } from "../lib/git";

function tone(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---")) return "text-slate-500";
  if (line.startsWith("+")) return "bg-emerald-50 text-emerald-800";
  if (line.startsWith("-")) return "bg-red-50 text-red-800";
  if (line.startsWith("@@")) return "text-sky-700";
  if (line.startsWith("\\")) return "text-slate-400 italic";
  return "text-slate-700";
}

export default function DiffView({
  text,
  hunkActions,
  compact = false,
}: {
  text: string;
  /** Knöpfe je Hunk (Index) — nur wo Stagen sinnvoll ist. */
  hunkActions?: (index: number) => ReactNode;
  compact?: boolean;
}) {
  if (!text.trim()) {
    return <p className="p-4 text-xs text-slate-400">Kein Unterschied.</p>;
  }
  const diff = parseDiff(text);
  const size = compact ? "text-[10.5px] leading-4" : "text-[11.5px] leading-5";
  return (
    <div className={`overflow-auto font-mono ${size}`}>
      {diff.header.length > 0 ? (
        <pre className="px-3 pt-2 text-slate-400">
          {diff.header.filter((line) => line.startsWith("diff ") || line.startsWith("rename") || line.startsWith("new file") || line.startsWith("deleted")).join("\n") || " "}
        </pre>
      ) : null}
      {diff.hunks.map((hunk, index) => (
        <section key={index} className="mt-1">
          <div className="flex items-center justify-between gap-2 border-y border-slate-100 bg-slate-50 px-3 py-0.5">
            <span className="truncate text-sky-700">{hunk.heading}</span>
            {hunkActions ? <span className="flex shrink-0 gap-1">{hunkActions(index)}</span> : null}
          </div>
          <pre className="px-3">
            {hunk.lines.slice(1).map((line, lineIndex) => (
              <div key={lineIndex} className={`whitespace-pre ${tone(line)}`}>
                {line || " "}
              </div>
            ))}
          </pre>
        </section>
      ))}
      {diff.hunks.length === 0 ? (
        <pre className="px-3 pb-2 text-slate-500">{diff.header.join("\n")}</pre>
      ) : null}
    </div>
  );
}
