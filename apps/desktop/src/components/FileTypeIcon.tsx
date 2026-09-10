/** File-name hints only: no content sniffing, no claim about language support. */
export function fileKind(path: string): "code" | "config" | "document" | "image" | "file" {
  const name = path.split(/[\\/]/).pop()?.toLowerCase() ?? "";
  const ext = name.split(".").pop() ?? "";
  if (/^(tsx?|jsx?|py|rs|go|java|cs|swift|kt|kts|c|cpp|h|hpp|rb|sh|ps1|sql|html|css|scss|vue|svelte)$/.test(ext)) return "code";
  if (/^(json|jsonc|ya?ml|toml|xml|ini|cfg|lock|env)$/.test(ext) || /^(dockerfile|makefile|\.gitignore|\.env(?:\..+)?)$/.test(name)) return "config";
  if (/^(md|mdx|txt|rst|pdf)$/.test(ext) || /^(license|readme|changelog)$/.test(name)) return "document";
  if (/^(svg|png|jpe?g|gif|webp|ico|avif|heic)$/.test(ext)) return "image";
  return "file";
}

const TONES = { folder: "amber", code: "blue", config: "violet", document: "teal", image: "rose", file: "slate" };
const LABELS = { folder: "Ordner", code: "Quelltext", config: "Konfiguration", document: "Dokument", image: "Bild", file: "Datei" };

export default function FileTypeIcon({ path, folder = false, open = false }: { path: string; folder?: boolean; open?: boolean }) {
  const kind = folder ? "folder" : fileKind(path);
  return (
    <span className="tone-ink inline-flex shrink-0" data-tone={TONES[kind]} data-file-kind={kind} title={LABELS[kind]}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {kind === "folder" ? <>
          <path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h3l1.5 1.5h4.5A1.5 1.5 0 0 1 14 6v6.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 12.5z" fill="currentColor" fillOpacity=".12" />
          {open && <path d="M2 7.5h12" />}
        </> : kind === "code" ? <>
          <path d="m5 4-3.5 4L5 12m6-8 3.5 4-3.5 4M9 3 7 13" />
        </> : kind === "config" ? <>
          <path d="M2 4h12M2 8h12M2 12h12" />
          <path d="M5 2v4m6 0v4m-5 0v4" strokeWidth="2.4" />
        </> : kind === "image" ? <>
          <rect x="2" y="2" width="12" height="12" rx="2" />
          <circle cx="10.5" cy="5.5" r="1" /><path d="m2 12 4-5 4 5 2-2 2 2" />
        </> : <>
          <path d="M3 2h6l4 4v8H3zM9 2v4h4" />
          {kind === "document" && <path d="M5.5 8h5M5.5 11h4" />}
        </>}
      </svg>
    </span>
  );
}
