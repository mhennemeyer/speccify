// Flaches `---`-Frontmatter zeilenweise zerlegen und wieder zusammenbauen —
// byte-stabil für unbekannte Zeilen (Playbooks, Specs im Editor).

/** Zerlegt einen Text in Frontmatter-Zeilen und Body (flach, zeilenbasiert). */
export function splitFrontmatter(text: string): { frontmatter: string[]; body: string } {
  text = text.replace(/^\uFEFF+/, "");
  const match = /^---\r?\n([\s\S]*?)^---(?:\r?\n|$)/m.exec(text);
  if (match?.index !== 0) return { frontmatter: [], body: text };
  return { frontmatter: match[1] ? match[1].replace(/\r?\n$/, "").split(/\r?\n/) : [], body: text.slice(match[0].length) };
}

/** Baut den Text neu: bekannte Felder ersetzt (oder ergänzt), unbekannte
 *  Frontmatter-Zeilen bleiben wörtlich erhalten, der Body kommt vom Editor. */
export function assembleFrontmatter(
  original: string,
  fields: Record<string, string>,
  body: string,
): string {
  const { frontmatter } = splitFrontmatter(original);
  const remaining = { ...fields };
  const replaced = new Set<string>();
  const lines = frontmatter.flatMap((line) => {
    const colon = line.indexOf(":");
    if (colon === -1) return [line];
    const key = line.slice(0, colon).trim();
    if (replaced.has(key)) return [];
    if (key in remaining) {
      const value = remaining[key];
      delete remaining[key];
      replaced.add(key);
      return [`${key}: ${value}`];
    }
    return [line];
  });
  for (const [key, value] of Object.entries(remaining)) {
    if (value.trim() !== "") lines.push(`${key}: ${value}`);
  }
  const bodyOut = body.endsWith("\n") ? body : body + "\n";
  if (lines.length === 0) return bodyOut;
  return `---\n${lines.join("\n")}\n---\n${bodyOut}`;
}

export function frontmatterValue(frontmatter: string[], key: string): string {
  for (const line of frontmatter) {
    const colon = line.indexOf(":");
    if (colon !== -1 && line.slice(0, colon).trim() === key) {
      return line.slice(colon + 1).trim();
    }
  }
  return "";
}
