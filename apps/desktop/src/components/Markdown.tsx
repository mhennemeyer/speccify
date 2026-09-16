// Markdown-Anzeige für Projektdateien (Pläne, SKILL.md). react-markdown
// rendert ohne rohes HTML — Projektdateien sind vertrauenswürdig, aber es
// gibt keinen Grund, HTML-Injection überhaupt zuzulassen.

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import MermaidDiagram from "./MermaidDiagram";

const components: Components = {
  pre({ node, children, ...props }) {
    const code = node?.children[0];
    if (code?.type === "element" && code.tagName === "code"
      && Array.isArray(code.properties.className)
      && code.properties.className.includes("language-mermaid")) {
      const source = code.children.map(child => child.type === "text" ? child.value : "").join("");
      return <MermaidDiagram source={source} />;
    }
    return <pre {...props}>{children}</pre>;
  },
};

/** `---`-Frontmatter abtrennen — die Metadaten zeigt die Liste, nicht der Body. */
export function stripFrontmatter(text: string): string {
  if (!text.startsWith("---\n")) return text;
  const end = text.indexOf("\n---", 4);
  if (end === -1) return text;
  return text.slice(end + 4).replace(/^\n+/, "");
}

export default function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{text}</ReactMarkdown>
    </div>
  );
}
