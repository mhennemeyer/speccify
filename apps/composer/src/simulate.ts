// Wiring-Simulation für den Bearbeiten-Modus: interpretiert die
// `composition.wiring`-Regeln des Dokuments — dieselbe Semantik wie der
// generierte React-Mock (`core/codegen/mock_react.py`): `set` schreibt in den
// wired-State, `emit` re-emittiert ein eigenes Event, Quellen sind
// `payload.<field>`, `props.<alias>.<prop>` oder Literale.
//
// Gerendert wird der echte Mock (siehe `mockRuntime.ts`); diese Simulation
// liefert nur die Props zwischen den einzeln gerenderten Knoten und das
// Event-Log. Im Vorschau-Modus läuft stattdessen die Verdrahtung des
// generierten Dokument-Mocks selbst — der Abgleich beider Wege ist gewollt.

import { findTreeNode } from "./doc";
import type { ChildInfo, SpecDoc } from "./types";

export type WiredState = Record<string, Record<string, unknown>>;

export interface FireResult {
  state: WiredState;
  emitted: { event: string; payload: Record<string, unknown> }[];
  setLog: string[];
}

export function mergedNodeProps(
  doc: SpecDoc,
  alias: string,
  children: Record<string, ChildInfo>,
  state: WiredState,
  ownProps: Record<string, unknown> = {},
): Record<string, unknown> {
  const merged: Record<string, unknown> = {};
  const contract = children[alias];
  // 1) Kind-Defaults aus dem API-Vertrag.
  for (const prop of contract?.api.props ?? []) {
    if (prop.hasDefault) merged[prop.name] = prop.default;
  }
  // 2) Statische Tree-Props (Knoten kann in einem Slot verschachtelt sein).
  const node = findTreeNode(doc.composition?.tree ?? [], alias);
  Object.assign(merged, node?.props ?? {});
  // 3) map_to-Weiterleitungen aus den eigenen Props (D3: explizit).
  for (const own of doc.api?.props ?? []) {
    if (!own.map_to) continue;
    const [targetAlias, targetProp] = own.map_to.split(".");
    if (targetAlias !== alias || !targetProp) continue;
    const value = ownProps[own.name] ?? own.default;
    if (value !== undefined) merged[targetProp] = value;
  }
  // 4) Wired-State (set-Regeln) gewinnt.
  Object.assign(merged, state[alias] ?? {});
  return merged;
}

function resolveSource(
  source: unknown,
  payload: Record<string, unknown>,
  doc: SpecDoc,
  children: Record<string, ChildInfo>,
  state: WiredState,
  ownProps: Record<string, unknown>,
): unknown {
  if (typeof source === "string" && source.startsWith("payload.")) {
    return payload[source.slice("payload.".length)];
  }
  if (typeof source === "string" && source.startsWith("props.")) {
    const [, alias, prop] = source.split(".");
    if (!alias || !prop) return undefined;
    return mergedNodeProps(doc, alias, children, state, ownProps)[prop];
  }
  return source;
}

export function fireEvent(
  doc: SpecDoc,
  children: Record<string, ChildInfo>,
  state: WiredState,
  ownProps: Record<string, unknown>,
  alias: string,
  eventName: string,
  payload: Record<string, unknown>,
): FireResult {
  const nextState: WiredState = JSON.parse(JSON.stringify(state)) as WiredState;
  const emitted: FireResult["emitted"] = [];
  const setLog: string[] = [];

  for (const rule of doc.composition?.wiring ?? []) {
    if (rule.when !== `${alias}.${eventName}`) continue;
    if (rule.set) {
      const [targetAlias, targetProp] = rule.set.split(".");
      if (targetAlias && targetProp) {
        const value = resolveSource(rule.to, payload, doc, children, nextState, ownProps);
        nextState[targetAlias] = { ...(nextState[targetAlias] ?? {}), [targetProp]: value };
        setLog.push(`${rule.set} ← ${JSON.stringify(value)}`);
      }
    }
    if (rule.emit) {
      const withMapping = rule.with ?? {};
      const eventPayload: Record<string, unknown> = {};
      for (const [field, source] of Object.entries(withMapping)) {
        eventPayload[field] = resolveSource(source, payload, doc, children, nextState, ownProps);
      }
      emitted.push({ event: rule.emit, payload: eventPayload });
    }
  }

  return { state: nextState, emitted, setLog };
}

