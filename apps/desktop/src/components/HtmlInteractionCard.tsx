// Ad-hoc-UI des Agenten (Spec 038): ein HTML-Fragment mit Tailwind-Klassen
// in einem sandboxed iframe (Skripte und Formulare erlaubt, kein Zugriff auf
// die App). Tailwind läuft als eingebettete Browser-Build im Frame, also
// offline. Eine Brücke meldet Formular-Submits, `data-answer`-Klicks und
// die Höhe per postMessage; die Antwort geht per `ui_answer` an den MCP.

import { useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
// Vendored copy of @tailwindcss/browser (the package exports only its entry, not the file).
import tailwindBrowser from "../assets/tailwind-browser.js?raw";
import type { AskBoInteraction } from "./AskBoPanel";

const BRIDGE = String.raw`
(function () {
  var id = window.name;
  function post(action, extra) {
    var message = { type: "speccify:ui", id: id, action: action };
    for (var key in extra) message[key] = extra[key];
    parent.postMessage(message, "*");
  }
  window.speccify = {
    submit: function (values) { post("submit", { values: values || {} }); },
    close: function () { post("close", {}); }
  };
  document.addEventListener("submit", function (event) {
    event.preventDefault();
    var form = event.target;
    var values = {};
    var data = new FormData(form);
    var multi = {};
    form.querySelectorAll("input[type=checkbox][name], select[multiple][name]").forEach(function (el) { multi[el.name] = true; });
    data.forEach(function (value, key) {
      if (key in values) { values[key] = [].concat(values[key], value); }
      else if (multi[key]) { values[key] = [value]; }
      else { values[key] = value; }
    });
    form.querySelectorAll("input[type=checkbox][name]").forEach(function (el) { if (!(el.name in values)) values[el.name] = []; });
    var button = event.submitter;
    if (button && button.name) values[button.name] = button.value;
    post("submit", { values: values });
  }, true);
  document.addEventListener("click", function (event) {
    var target = event.target && event.target.closest ? event.target.closest("[data-answer]") : null;
    if (target) { event.preventDefault(); post("submit", { values: { answer: target.getAttribute("data-answer") } }); }
  });
  function report() { post("height", { height: document.documentElement.scrollHeight }); }
  if (window.ResizeObserver) new ResizeObserver(report).observe(document.body);
  window.addEventListener("load", report);
  setTimeout(report, 50);
})();
`;

function documentFor(html: string): string {
  return [
    "<!doctype html><html><head><meta charset=\"utf-8\">",
    `<script>${tailwindBrowser}</script>`,
    "<style>body{margin:0;padding:10px;font:13px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;color:#0f172a;background:#fff}</style>",
    "</head><body>",
    html,
    // Die Brücke läuft nach dem Inhalt, damit body und Formulare existieren.
    `<script>${BRIDGE}</script>`,
    "</body></html>",
  ].join("");
}

export default function HtmlInteractionCard({ interaction }: { interaction: AskBoInteraction }) {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(120);
  const [error, setError] = useState<string | null>(null);
  const [closed, setClosed] = useState(false);
  const done = interaction.answered !== undefined || closed;
  const srcdoc = useMemo(() => documentFor(interaction.html ?? ""), [interaction.html]);

  const send = (values: Record<string, unknown>) => {
    setError(null);
    void invoke("ui_answer", { id: interaction.id, values }).catch((e) => setError(String(e)));
  };

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const frame = frameRef.current;
      if (!frame || event.source !== frame.contentWindow) return;
      const data = event.data as { type?: string; id?: string; action?: string; values?: Record<string, unknown>; height?: number };
      if (data?.type !== "speccify:ui" || data.id !== interaction.id) return;
      if (data.action === "height" && typeof data.height === "number") {
        setHeight(Math.max(60, Math.min(640, Math.ceil(data.height) + 4)));
      } else if (data.action === "submit" && !done) {
        send(data.values ?? {});
      } else if (data.action === "close" && !done) {
        setClosed(true);
        send({ closed: true });
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interaction.id, done]);

  const values = interaction.answered?.values;
  const closedOnly = !!values && Object.keys(values).length === 1 && values.closed === true;
  return (
    <div className={`rounded border border-slate-600 bg-slate-900 p-2 text-sm ${done ? "opacity-70" : ""}`} data-ui-interaction={interaction.id} data-ui-mode={interaction.mode ?? "ask"}>
      <div className="mb-1.5 flex items-center gap-2">
        <span className="font-medium text-slate-200">{interaction.title || interaction.prompt}</span>
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{interaction.mode === "show" ? "Anzeige" : "Frage"}</span>
        {!done && interaction.mode === "show" ? (
          <button
            onClick={() => { setClosed(true); send({ closed: true }); }}
            className="ml-auto rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-200 hover:bg-slate-600"
          >
            Schließen
          </button>
        ) : null}
      </div>
      <iframe
        ref={frameRef}
        name={interaction.id}
        title={interaction.title || interaction.prompt}
        sandbox="allow-scripts allow-forms"
        srcDoc={srcdoc}
        style={{ height, pointerEvents: done ? "none" : "auto" }}
        className="w-full rounded bg-white"
      />
      {values && Object.keys(values).length > 0 && !closedOnly ? (
        <p className="mt-1 truncate font-mono text-[11px] text-emerald-400" title={JSON.stringify(values)}>
          Antwort: {JSON.stringify(values)}
        </p>
      ) : done ? (
        <p className="mt-1 text-[11px] text-slate-500">{interaction.mode === "show" ? "geschlossen" : "beantwortet"}</p>
      ) : null}
      {error ? <p className="mt-1 text-[11px] text-red-400">{error}</p> : null}
    </div>
  );
}
