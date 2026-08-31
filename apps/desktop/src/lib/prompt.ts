// „Als Prompt kopieren" (P5/W6): ein fertiger Markdown-Block mit
// Pfad-Referenz und Zaun, dessen Länge gegen Backticks im Inhalt
// berechnet ist — der Übergabekanal an den Agenten im Terminal.

import { writeText } from "@tauri-apps/plugin-clipboard-manager";

export function fencedPrompt(reference: string, content: string): string {
  const runs = content.match(/`+/g) ?? [];
  const fence = "`".repeat(Math.max(3, ...runs.map((run) => run.length + 1)));
  return `\`${reference}\`\n\n${fence}md\n${content.trimEnd()}\n${fence}\n`;
}

export async function copyPrompt(reference: string, content: string): Promise<void> {
  await writeText(fencedPrompt(reference, content));
}
