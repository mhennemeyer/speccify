import { useEffect, useState } from "react";
import DOMPurify from "dompurify";

// Mermaid has process-wide configuration and temporary DOM. Keep initialize/render
// together, including when several documents or theme changes render concurrently.
let pending: Promise<unknown> = Promise.resolve();
let nextId = 0;

function renderDiagram(source: string, dark: boolean, cancelled: () => boolean): Promise<string> {
  const job = pending.catch(() => {}).then(async () => {
    if (cancelled()) return "";
    if (source.length > 50_000) throw new Error("Diagramm ist zu groß (maximal 50.000 Zeichen).");
    const { default: mermaid } = await import("mermaid");
    if (cancelled()) return "";
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      suppressErrorRendering: true,
      theme: dark ? "dark" : "default",
      fontFamily: "Arial, sans-serif",
      htmlLabels: false,
      flowchart: { htmlLabels: false },
      // Document directives must not weaken the host's rendering policy.
      secure: ["secure", "securityLevel", "startOnLoad", "maxTextSize", "maxEdges",
        "suppressErrorRendering", "htmlLabels", "flowchart", "themeCSS", "themeVariables"],
    });
    const host = document.createElement("div");
    host.setAttribute("aria-hidden", "true");
    // Hidden tabs have no layout. Measure in a connected, off-screen container.
    host.style.cssText = "position:fixed;left:-100000px;top:0;width:1200px;visibility:hidden;pointer-events:none";
    document.body.append(host);
    try {
      const { svg } = await mermaid.render(`speccify-mermaid-${++nextId}`, source, host);
      // SVG is library output, never raw document HTML. Do not bind callbacks or links.
      return DOMPurify.sanitize(svg, {
        USE_PROFILES: { svg: true, svgFilters: true },
        FORBID_TAGS: ["foreignObject", "image", "a"],
        FORBID_ATTR: ["href", "xlink:href"],
      });
    } finally {
      host.remove();
    }
  });
  pending = job;
  return job;
}

export default function MermaidDiagram({ source }: { source: string }) {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === "dark");
  const [result, setResult] = useState<{ source: string; dark: boolean; svg?: string; error?: string }>();
  useEffect(() => {
    const observer = new MutationObserver(() => setDark(document.documentElement.dataset.theme === "dark"));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    let cancelled = false;
    void renderDiagram(source, dark, () => cancelled).then(
      svg => { if (!cancelled) setResult({ source, dark, svg }); },
      error => { if (!cancelled) setResult({ source, dark, error: String(error) }); },
    );
    return () => { cancelled = true; };
  }, [source, dark]);
  const current = result?.source === source && result.dark === dark ? result : undefined;
  return (
    <figure className="mermaid-diagram" aria-label="Mermaid-Diagramm">
      {current?.svg ? <div className="mermaid-svg" role="img" aria-label="Diagramm" dangerouslySetInnerHTML={{ __html: current.svg }} />
        : <p role="status">{current?.error ? "Diagramm konnte nicht dargestellt werden." : "Diagramm wird geladen…"}</p>}
      {current?.error && <pre className="mermaid-error">{current.error}</pre>}
      <details open={!!current?.error}>
        <summary>Mermaid-Quelltext</summary>
        <pre><code>{source}</code></pre>
      </details>
    </figure>
  );
}
