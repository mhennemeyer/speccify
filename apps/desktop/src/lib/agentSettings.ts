import codex from "./schemas/codex.json";
import claude from "./schemas/claude.json";
import { t } from "../i18n";

interface Schema {
  $ref?: string; type?: string | string[]; description?: string; enum?: unknown[];
  properties?: Record<string, Schema>; additionalProperties?: boolean | Schema;
  allOf?: Schema[]; anyOf?: Schema[]; oneOf?: Schema[];
  minimum?: number; maximum?: number;
}
export interface SettingField { path: string[]; help: string; type: string; options?: unknown[]; group: string; minimum?: number; maximum?: number }
const schemas: Record<string, Schema> = { "codex-config": codex as unknown as Schema, "claude-settings": claude as unknown as Schema };
function resolve(schema: Schema, root: Schema, depth = 0): Schema {
  if (depth > 12) return schema;
  if (schema.$ref?.startsWith("#/")) {
    let target: unknown = root;
    for (const part of schema.$ref.slice(2).split("/")) target = (target as Record<string, unknown>)?.[part];
    return { ...resolve((target ?? {}) as Schema, root, depth + 1), ...schema, $ref: undefined };
  }
  if (schema.allOf?.length === 1) return { ...resolve(schema.allOf[0], root, depth + 1), ...schema, allOf: undefined };
  const variants = schema.oneOf ?? schema.anyOf;
  if (variants) {
    const options = variants.map(s => resolve(s, root, depth + 1));
    if (options.every(s => s.enum)) return { ...schema, type: "string", enum: options.flatMap(s => s.enum ?? []) };
    return { ...schema, type: "json" };
  }
  return schema;
}
function group(path: string[]) {
  const key = path.join(".").toLowerCase();
  if (/permission|approval|sandbox|trust|network|writable|allow|deny|auto_review/.test(key)) return t("Berechtigungen und Sandbox");
  if (/model|reason|effort|thinking|token|context|compact/.test(key)) return t("Modell und Denken");
  if (/tui|notif|theme|output|terminal|status|language/.test(key)) return t("Terminal und Darstellung");
  if (/mcp|hook|plugin|skill|tool|apps|agent/.test(key)) return t("Tools und Erweiterungen");
  if (/auth|login|key|provider|credential|env|proxy/.test(key)) return t("Anmeldung und Umgebung");
  return t("Weitere Einstellungen");
}
const overrides: Record<string, Partial<SettingField>> = {
  approval_policy: { type: "json", options: ["on-request", "never"], help: "on-request: Der Host entscheidet, wann eine Freigabe nötig ist. never: Keine Rückfrage; gesperrte Aktionen scheitern stattdessen. Granulare Regeln können als JSON gesetzt werden." },
  approvals_reviewer: { help: "user fragt Dich. auto_review lässt geeignete Freigaben automatisch prüfen. Eine Ablehnung bleibt möglich; Sandbox und Admin-Regeln gelten weiter. Benötigt eine aktuelle Codex-Version." },
  sandbox_mode: { help: "workspace-write erlaubt Änderungen im Arbeitsordner. read-only ist nur lesend. danger-full-access entfernt die Sandbox-Grenzen. Netzwerk und zusätzliche Schreibordner sind gesondert einstellbar." },
  "windows.sandbox": { help: "Native Windows-Sandbox: elevated ist empfohlen und benötigt die einmalige Einrichtung durch Codex mit Windows-Freigabe. unelevated ist der eingeschränkte Fallback. Unter WSL gelten die Linux-Einstellungen." },
  "permissions.defaultMode": { help: "auto prüft Befehle automatisch, soweit Konto, Modell und Admin dies erlauben. acceptEdits erlaubt Dateiänderungen, fragt bei vielen Befehlen weiter. default fragt regulär, plan plant, bypassPermissions überspringt Berechtigungsprüfungen." },
};
export function settingsFields(id: string): SettingField[] {
  const root = schemas[id];
  if (!root) return [];
  const result: SettingField[] = [];
  function walk(properties: Record<string, Schema>, parent: string[], depth: number) {
    for (const [key, raw] of Object.entries(properties)) {
      const schema = resolve(raw, root), path = [...parent, key];
      if (schema.properties && depth < 4 && !schema.additionalProperties) walk(schema.properties, path, depth + 1);
      else result.push({ path, help: schema.description ?? raw.description ?? t("Strukturierter Host-Wert. Einzelheiten in der Referenz; komplexe Werte als JSON bearbeiten."),
        type: typeof schema.type === "string" ? schema.type : "json", options: schema.enum, group: group(path),
        minimum: schema.minimum, maximum: schema.maximum, ...overrides[path.join(".")] });
    }
  }
  walk(root.properties ?? {}, [], 0);
  return result.sort((a, b) => a.path.join(".").localeCompare(b.path.join(".")));
}
export function settingValue(value: unknown, path: string[]): unknown {
  for (const part of path) value = (value as Record<string, unknown>)?.[part];
  return value;
}
export const settingsReferences: Record<string, string> = {
  "codex-config": "https://learn.chatgpt.com/docs/config-file/config-reference",
  "claude-settings": "https://code.claude.com/docs/en/settings",
};
export const autonomySettings: Record<string, Record<string, unknown>> = {
  "codex-config": { approval_policy: "on-request", approvals_reviewer: "auto_review", sandbox_mode: "workspace-write",
    "tui.notifications": true, "tui.notification_method": "osc9", "tui.notification_condition": "always" },
  "claude-settings": { "permissions.defaultMode": "auto" },
};
