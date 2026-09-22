// Spec 065: Fragen und Antworten des Agenten als Markdown — Absätze, Listen,
// Code — und jedes Code-Stück mit einem Kopierknopf, weil das meistens genau
// der Text ist, den der Mensch in ein Terminal übertragen soll.

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";

/** Einzelne Zeilenumbrüche des Agenten bleiben Umbrüche (harter Umbruch),
 *  Leerzeilen werden Absätze; Codeblöcke bleiben unangetastet. */
export function preserveLineBreaks(text: string): string {
  const parts = text.split(/(```[\s\S]*?```)/);
  return parts
    .map((part, index) => (index % 2 === 1 ? part : part.replace(/([^\n])\n(?!\n)/g, "$1  \n")))
    .join("");
}

function CopyButton({ text, block = false }: { text: string; block?: boolean }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), 1800);
    return () => clearTimeout(timer);
  }, [state]);
  return (
    <button
      type="button"
      data-copy-code={text}
      title="In die Zwischenablage kopieren"
      onClick={(event) => {
        event.stopPropagation();
        void writeText(text).then(() => setState("copied")).catch(() => setState("failed"));
      }}
      className={`${block ? "absolute right-2 top-2" : "ml-1 align-middle"} rounded border px-1 py-px text-[10px] leading-4 ${
        state === "copied" ? "border-emerald-300 bg-emerald-50 text-emerald-700"
          : state === "failed" ? "border-red-300 bg-red-50 text-red-700"
          : "border-orange-300 bg-white text-orange-700 hover:bg-orange-100"
      }`}
    >
      {state === "copied" ? "✓ kopiert" : state === "failed" ? "Kopieren fehlgeschlagen" : "Kopieren"}
    </button>
  );
}

const components: Components = {
  code({ node, className, children, ...props }) {
    const text = String(children).replace(/\n$/, "");
    // Inline: ein Kind-Text ohne Zeilenumbruch und ohne Sprachklasse. Blöcke
    // rendert `pre` unten samt Knopf, hier bleiben sie unverändert.
    const inline = !className && !text.includes("\n") && node?.position?.start.line === node?.position?.end.line;
    if (!inline) return <code className={className} {...props}>{children}</code>;
    return (
      <span className="inline-flex flex-wrap items-baseline gap-0.5">
        <code data-question-code className="rounded border border-orange-200 bg-white px-1 py-px font-mono text-[0.8rem] text-orange-950" {...props}>{children}</code>
        <CopyButton text={text} />
      </span>
    );
  },
  pre({ node, children, ...props }) {
    const code = node?.children[0];
    const source = code?.type === "element" ? code.children.map((child) => (child.type === "text" ? child.value : "")).join("") : "";
    return (
      <span className="relative block">
        <pre data-question-block {...props}>{children}</pre>
        <CopyButton text={source.replace(/\n$/, "")} block />
      </span>
    );
  },
};

export default function QuestionText({ text }: { text: string }) {
  return (
    <div className="markdown-body question-text text-sm text-orange-900" data-question-text>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{preserveLineBreaks(text)}</ReactMarkdown>
    </div>
  );
}
