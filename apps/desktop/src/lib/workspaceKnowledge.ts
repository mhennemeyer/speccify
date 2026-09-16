export type KnowledgeKind = "skills" | "tools" | "mcps" | "playbooks";
export interface KnowledgeEntry {
  key: string; kind: KnowledgeKind; name: string; title: string; file: string;
  absolute_path: string; worktree_id: string; source: string; root: string;
  status: string; host: "codex" | "claude" | null;
}
export interface KnowledgeSource { id: string; name: string; path: string; available: boolean; errors: string[] }
export interface KnowledgeCatalog { entries: KnowledgeEntry[]; sources: KnowledgeSource[]; warnings: string[] }
export interface KnowledgeSelection { file: string; name: string; host?: string | null; request: number; manage?: boolean }
export function isKnowledge(value: string): value is KnowledgeKind { return ["skills", "tools", "mcps", "playbooks"].includes(value); }
export function mcpConnectionPrompt(entry: KnowledgeEntry, root: string): string {
  return `Prüfe die gezielte Host-Anbindung dieses MCPs.\nWorkspace und Ziel: ${root}\nQuelle: ${entry.absolute_path}\nQuellprojekt/cwd: ${entry.root}\nHost: ${entry.host}\nServername in dieser Quelle: ${entry.name}\nEindeutige Katalog-ID: ${entry.key}\nLies ausschließlich diese Definition und die geltenden Projektregeln. Prüfe Befehl/URL, relative Pfade, benötigte Umgebungsvariablen und Zugangskontext. Nutze einen eindeutigen Namen für diesen Quellserver. Bestehende Host-Konfiguration und Allowlists nicht überschreiben oder zusammenführen; Zugangsdaten nicht in den Chat oder getrackte Dateien kopieren. Lege die konkrete Anbindung zur Prüfung vor, bevor Du sie aktivierst. Erst nach erfolgreichem Handshake und tools/list im gewählten Root-Host ist dieser Server dort nutzbar. Ein erfolgreicher Test in einem anderen Prozess genügt dafür nicht.`;
}
