// Code-Editor auf CodeMirror 6 (Plan ide-im-projektfenster.md, I1/E2, I3).
// Ein EditorView pro geöffneter Datei (der Aufrufer setzt `key={path}`),
// Sprache nach Endung, Thema folgt `data-theme` am <html>, Cmd/Ctrl-S
// ruft `onSave`. Der Inhalt fließt nur nach außen (onChange) — von außen
// kommt ein neuer Text nur über `key`-Wechsel oder `revision`. I3: Sprung
// zu einer Zeile (`reveal`) und Blame am Rand (`blame`, eigene Gutter).

import { useEffect, useRef } from "react";
import { EditorView, basicSetup } from "codemirror";
import { EditorState, Compartment } from "@codemirror/state";
import { GutterMarker, gutter, keymap } from "@codemirror/view";
import { indentWithTab } from "@codemirror/commands";
import { markdown } from "@codemirror/lang-markdown";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { rust } from "@codemirror/lang-rust";
import { json } from "@codemirror/lang-json";
import { yaml } from "@codemirror/lang-yaml";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { oneDark } from "@codemirror/theme-one-dark";
import type { Extension } from "@codemirror/state";
import type { BlameLine } from "../lib/git";

export function languageFor(path: string): Extension {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "md":
    case "markdown":
      return markdown();
    case "ts":
    case "mts":
    case "cts":
      return javascript({ typescript: true });
    case "tsx":
      return javascript({ typescript: true, jsx: true });
    case "js":
    case "mjs":
    case "cjs":
      return javascript();
    case "jsx":
      return javascript({ jsx: true });
    case "py":
      return python();
    case "rs":
      return rust();
    case "json":
    case "jsonc":
      return json();
    case "yml":
    case "yaml":
      return yaml();
    case "html":
    case "htm":
    case "astro":
      return html();
    case "css":
      return css();
    default:
      return [];
  }
}

function isDarkNow(): boolean {
  return document.documentElement.dataset.theme === "dark";
}

class BlameMarker extends GutterMarker {
  constructor(
    private readonly text: string,
    private readonly title: string,
    private readonly muted: boolean,
  ) {
    super();
  }

  override eq(other: BlameMarker) {
    return other.text === this.text && other.muted === this.muted;
  }

  override toDOM() {
    const span = document.createElement("span");
    span.textContent = this.text;
    span.title = this.title;
    span.className = this.muted ? "cm-blame-muted" : "";
    return span;
  }
}

/// Blame als Gutter: je Zeile Kurz-Hash + Autor; wiederholte Commits
/// direkt untereinander werden gedämpft, damit Blöcke lesbar bleiben.
function blameGutter(lines: BlameLine[]): Extension {
  if (lines.length === 0) return [];
  const byLine = new Map<number, BlameLine>();
  for (const entry of lines) byLine.set(entry.line, entry);
  return [
    gutter({
      class: "cm-blame",
      lineMarker(view, line) {
        const number = view.state.doc.lineAt(line.from).number;
        const entry = byLine.get(number);
        if (!entry) return null;
        const previous = byLine.get(number - 1);
        const muted = previous !== undefined && previous.short === entry.short;
        const author = entry.author.split(" ")[0] ?? entry.author;
        return new BlameMarker(
          muted ? "·" : `${entry.short} ${author}`,
          `${entry.short} · ${entry.author} · ${entry.date}\n${entry.summary}`,
          muted,
        );
      },
    }),
    EditorView.theme({
      ".cm-blame": {
        minWidth: "12ch",
        color: "#64748b",
        fontSize: "10px",
        borderRight: "1px solid rgba(148,163,184,0.35)",
        paddingRight: "6px",
      },
      ".cm-blame .cm-gutterElement": { textAlign: "left", whiteSpace: "nowrap", overflow: "hidden" },
      ".cm-blame-muted": { opacity: "0.35" },
    }),
  ];
}

export default function CodeEditor({
  path,
  value,
  revision = 0,
  onChange,
  onSave,
  onCursor,
  reveal,
  blame,
}: {
  path: string;
  value: string;
  /** Hochzählen, wenn der Text von außen ersetzt wurde (Reload). */
  revision?: number;
  onChange: (text: string) => void;
  onSave: () => void;
  onCursor?: (line: number) => void;
  /** Zeile anspringen; `nonce` erzwingt den Sprung auch zur selben Zeile. */
  reveal?: { line: number; nonce: number } | null;
  /** Blame je Zeile (git_cmd::project_git_blame) — `null` = aus. */
  blame?: BlameLine[] | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const theme = useRef(new Compartment());
  const blameCompartment = useRef(new Compartment());
  const onChangeRef = useRef(onChange);
  const onSaveRef = useRef(onSave);
  const onCursorRef = useRef(onCursor);
  onChangeRef.current = onChange;
  onSaveRef.current = onSave;
  onCursorRef.current = onCursor;

  useEffect(() => {
    if (!host.current) return;
    const state = EditorState.create({
      doc: value,
      extensions: [
        basicSetup,
        keymap.of([
          {
            key: "Mod-s",
            run: () => {
              onSaveRef.current();
              return true;
            },
          },
          indentWithTab,
        ]),
        languageFor(path),
        theme.current.of(isDarkNow() ? oneDark : []),
        blameCompartment.current.of(blameGutter(blame ?? [])),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) onChangeRef.current(update.state.doc.toString());
          if (update.selectionSet || update.docChanged) {
            const line = update.state.doc.lineAt(update.state.selection.main.head).number;
            onCursorRef.current?.(line);
          }
        }),
        EditorView.theme({
          "&": { height: "100%", fontSize: "12.5px" },
          ".cm-scroller": { fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" },
        }),
      ],
    });
    const editor = new EditorView({ state, parent: host.current });
    view.current = editor;

    // Thema live mitziehen (Sonne/Mond in der Toolbar).
    const observer = new MutationObserver(() => {
      editor.dispatch({ effects: theme.current.reconfigure(isDarkNow() ? oneDark : []) });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    return () => {
      observer.disconnect();
      editor.destroy();
      view.current = null;
    };
    // Neuer Text von außen = neue Instanz (key/revision), nicht patchen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, revision]);

  // Blame ein-/ausschalten oder aktualisieren, ohne den Editor neu zu bauen.
  useEffect(() => {
    view.current?.dispatch({
      effects: blameCompartment.current.reconfigure(blameGutter(blame ?? [])),
    });
  }, [blame]);

  // Zeile anspringen (Suche, Terminal-Link, Git).
  useEffect(() => {
    const editor = view.current;
    if (!editor || !reveal) return;
    const doc = editor.state.doc;
    const number = Math.min(Math.max(1, reveal.line), doc.lines);
    const pos = doc.line(number).from;
    editor.dispatch({
      selection: { anchor: pos },
      effects: EditorView.scrollIntoView(pos, { y: "center" }),
    });
    editor.focus();
  }, [reveal, revision]);

  return <div ref={host} className="h-full min-h-0 overflow-hidden text-left" />;
}
