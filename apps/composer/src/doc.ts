// Dokument-Modell des Composers: ein `SpecDoc` spiegelt die Spec-YAML 1:1 —
// der Composer ist ein Spec-Editor, kein Codegenerator (Round-Trip-Prinzip).

import { dump, load } from "js-yaml";

import type {
  ChildInfo,
  SpecDoc,
  TreeNodeData,
  WiringRuleData,
} from "./types";

export function newComposite(name: string, kind: "ui-component" | "app"): SpecDoc {
  return {
    schema_version: 1,
    id: `@org/${name}`,
    version: "0.1.0",
    kind,
    title: name,
    summary: `Im Composer gebaute ${kind === "app" ? "App" : "Composite-Komponente"}: ${name}.`,
    license: "MIT",
    api: { props: [], events: [] },
    composition: { uses: {}, tree: [], wiring: [] },
  };
}

export function docToYaml(doc: SpecDoc): string {
  // Bewusst schlanke Serialisierung: leere Blöcke fallen weg, Key-Reihenfolge
  // folgt dem Dokument (js-yaml `sortKeys: false` ist Default).
  const out: Record<string, unknown> = {
    schema_version: doc.schema_version,
    id: doc.id,
    version: doc.version,
    kind: doc.kind,
    title: doc.title,
    summary: doc.summary,
  };
  if (doc.license) out.license = doc.license;
  const props = doc.api?.props ?? [];
  const events = doc.api?.events ?? [];
  if (props.length > 0 || events.length > 0) {
    const api: Record<string, unknown> = {};
    if (props.length > 0) api.props = props;
    if (events.length > 0) api.events = events;
    out.api = api;
  }
  if (doc.composition && Object.keys(doc.composition.uses).length > 0) {
    const composition: Record<string, unknown> = {
      uses: doc.composition.uses,
      tree: doc.composition.tree,
    };
    if ((doc.composition.wiring ?? []).length > 0) {
      composition.wiring = doc.composition.wiring;
    }
    out.composition = composition;
  }
  return dump(out, { lineWidth: 100, noRefs: true });
}

export function yamlToDoc(yamlText: string): SpecDoc {
  const parsed = load(yamlText);
  if (typeof parsed !== "object" || parsed === null) {
    throw new Error("Spec-YAML ist kein Mapping.");
  }
  return parsed as SpecDoc;
}

// --- Mutationen (immutabel: liefern neue Dokumente) ---------------------------

function cloneDoc(doc: SpecDoc): SpecDoc {
  return JSON.parse(JSON.stringify(doc)) as SpecDoc;
}

function ensureComposition(doc: SpecDoc): asserts doc is SpecDoc & {
  composition: NonNullable<SpecDoc["composition"]>;
} {
  if (!doc.composition) {
    doc.composition = { uses: {}, tree: [], wiring: [] };
  }
}

export function suggestAlias(doc: SpecDoc, specId: string): string {
  const base = specId.split("/")[1]?.replace(/-/g, "_") ?? "node";
  const taken = new Set(Object.keys(doc.composition?.uses ?? {}));
  if (!taken.has(base)) return base;
  let counter = 2;
  while (taken.has(`${base}_${counter}`)) counter += 1;
  return `${base}_${counter}`;
}

export function addChild(doc: SpecDoc, child: ChildInfo): { doc: SpecDoc; alias: string } {
  const next = cloneDoc(doc);
  ensureComposition(next);
  const alias = suggestAlias(next, child.id);
  const [major, minor] = child.version.split(".");
  next.composition.uses[alias] = `${child.id}@^${major}.${minor}`;
  next.composition.tree.push({ node: alias });
  return { doc: next, alias };
}

export function removeChild(doc: SpecDoc, alias: string): SpecDoc {
  const next = cloneDoc(doc);
  ensureComposition(next);
  delete next.composition.uses[alias];
  next.composition.tree = next.composition.tree.filter((node) => node.node !== alias);
  next.composition.wiring = (next.composition.wiring ?? []).filter(
    (rule) =>
      !rule.when.startsWith(`${alias}.`) && !(rule.set ?? "").startsWith(`${alias}.`),
  );
  if (next.api?.props) {
    next.api.props = next.api.props.map((prop) =>
      (prop.map_to ?? "").startsWith(`${alias}.`) ? { ...prop, map_to: undefined } : prop,
    );
  }
  return next;
}

export function setTreeProp(
  doc: SpecDoc,
  alias: string,
  propName: string,
  value: unknown,
): SpecDoc {
  const next = cloneDoc(doc);
  ensureComposition(next);
  const node = next.composition.tree.find((entry) => entry.node === alias);
  if (!node) return doc;
  const props: Record<string, unknown> = { ...(node.props ?? {}) };
  if (value === undefined || value === "") {
    delete props[propName];
  } else {
    props[propName] = value;
  }
  if (Object.keys(props).length > 0) {
    node.props = props;
  } else {
    delete node.props;
  }
  return next;
}

export function moveNode(doc: SpecDoc, alias: string, direction: -1 | 1): SpecDoc {
  const next = cloneDoc(doc);
  ensureComposition(next);
  const tree = next.composition.tree;
  const index = tree.findIndex((node) => node.node === alias);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= tree.length) return doc;
  const swapped: TreeNodeData = tree[target];
  tree[target] = tree[index];
  tree[index] = swapped;
  return next;
}

export function addWiringRule(doc: SpecDoc, rule: WiringRuleData): SpecDoc {
  const next = cloneDoc(doc);
  ensureComposition(next);
  next.composition.wiring = [...(next.composition.wiring ?? []), rule];
  return next;
}

export function removeWiringRule(doc: SpecDoc, index: number): SpecDoc {
  const next = cloneDoc(doc);
  ensureComposition(next);
  next.composition.wiring = (next.composition.wiring ?? []).filter((_, i) => i !== index);
  return next;
}

export function upsertOwnEvent(
  doc: SpecDoc,
  name: string,
  payload: Record<string, string>,
): SpecDoc {
  const next = cloneDoc(doc);
  next.api = next.api ?? {};
  const events = [...(next.api.events ?? [])];
  const entry = Object.keys(payload).length > 0 ? { name, payload } : { name };
  const index = events.findIndex((event) => event.name === name);
  if (index >= 0) {
    events[index] = entry;
  } else {
    events.push(entry);
  }
  next.api.events = events;
  return next;
}

export function removeOwnEvent(doc: SpecDoc, name: string): SpecDoc {
  const next = cloneDoc(doc);
  if (!next.api?.events) return next;
  next.api.events = next.api.events.filter((event) => event.name !== name);
  next.composition = next.composition ?? { uses: {}, tree: [], wiring: [] };
  next.composition.wiring = (next.composition.wiring ?? []).filter(
    (rule) => rule.emit !== name,
  );
  return next;
}

export function upsertOwnProp(
  doc: SpecDoc,
  prop: { name: string; type: string; default?: unknown; map_to?: string },
): SpecDoc {
  const next = cloneDoc(doc);
  next.api = next.api ?? {};
  const props = [...(next.api.props ?? [])];
  const index = props.findIndex((p) => p.name === prop.name);
  const entry = { ...prop };
  if (entry.map_to === "") delete entry.map_to;
  if (entry.default === "" || entry.default === undefined) delete entry.default;
  if (index >= 0) {
    props[index] = entry;
  } else {
    props.push(entry);
  }
  next.api.props = props;
  return next;
}

export function removeOwnProp(doc: SpecDoc, name: string): SpecDoc {
  const next = cloneDoc(doc);
  if (!next.api?.props) return next;
  next.api.props = next.api.props.filter((prop) => prop.name !== name);
  return next;
}

export function renameSpec(doc: SpecDoc, name: string): SpecDoc {
  const next = cloneDoc(doc);
  next.id = `@org/${name}`;
  next.title = name;
  return next;
}
