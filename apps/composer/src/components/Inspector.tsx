import { useState } from "react";

import {
  addWiringRule,
  moveNode,
  removeChild,
  removeOwnEvent,
  removeOwnProp,
  removeWiringRule,
  renameSpec,
  setTreeProp,
  upsertOwnEvent,
  upsertOwnProp,
} from "../doc";
import type {
  ChildInfo,
  PropContract,
  SpecDoc,
  WiringRuleData,
} from "../types";

interface InspectorProps {
  doc: SpecDoc | null;
  childrenInfo: Record<string, ChildInfo>;
  selection: string | null;
  onDocChange: (doc: SpecDoc) => void;
  onChildrenChange: (
    update: (current: Record<string, ChildInfo>) => Record<string, ChildInfo>,
  ) => void;
  onSelectionChange: (alias: string | null) => void;
}

type Tab = "node" | "wiring" | "api" | "spec";

export function Inspector(props: InspectorProps) {
  const [tab, setTab] = useState<Tab>("node");
  const { doc } = props;

  if (!doc) {
    return (
      <aside className="inspector">
        <p className="muted">Keine Spec geöffnet.</p>
      </aside>
    );
  }

  return (
    <aside className="inspector">
      <div className="tabs">
        {(
          [
            ["node", "Knoten"],
            ["wiring", "Verdrahtung"],
            ["api", "API"],
            ["spec", "Spec"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            className={tab === key ? "active" : ""}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "node" ? <NodePanel {...props} doc={doc} /> : null}
      {tab === "wiring" ? <WiringPanel {...props} doc={doc} /> : null}
      {tab === "api" ? <OwnApiPanel {...props} doc={doc} /> : null}
      {tab === "spec" ? <SpecPanel {...props} doc={doc} /> : null}
    </aside>
  );
}

// --- Knoten-Panel -------------------------------------------------------------

function NodePanel({
  doc,
  childrenInfo,
  selection,
  onDocChange,
  onChildrenChange,
  onSelectionChange,
}: InspectorProps & { doc: SpecDoc }) {
  if (!selection) {
    return <p className="muted">Knoten im Canvas anklicken.</p>;
  }
  const child = childrenInfo[selection];
  const node = doc.composition?.tree.find((entry) => entry.node === selection);
  if (!child || !node) {
    return <p className="muted">Knoten „{selection}" nicht gefunden.</p>;
  }

  return (
    <div>
      <h2>
        {selection} · {child.title}
      </h2>
      <div className="row" style={{ marginBottom: 12 }}>
        <button className="small" onClick={() => onDocChange(moveNode(doc, selection, -1))}>
          ↑
        </button>
        <button className="small" onClick={() => onDocChange(moveNode(doc, selection, 1))}>
          ↓
        </button>
        <button
          className="small danger"
          onClick={() => {
            onDocChange(removeChild(doc, selection));
            onChildrenChange((current) => {
              const next = { ...current };
              delete next[selection];
              return next;
            });
            onSelectionChange(null);
          }}
        >
          entfernen
        </button>
      </div>
      {child.api.props.map((prop) => (
        <TreePropEditor
          key={prop.name}
          prop={prop}
          value={node.props?.[prop.name]}
          onChange={(value) => onDocChange(setTreeProp(doc, selection, prop.name, value))}
        />
      ))}
      {child.api.props.length === 0 ? <p className="muted">Keine Props.</p> : null}
    </div>
  );
}

function TreePropEditor({
  prop,
  value,
  onChange,
}: {
  prop: PropContract;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const id = `tree-prop-${prop.name}`;
  const placeholder = prop.hasDefault ? `Default: ${JSON.stringify(prop.default)}` : "";
  return (
    <div className="field">
      <label htmlFor={id}>
        {prop.name}: {prop.type.raw}
        {prop.required ? " *" : ""}
      </label>
      {prop.type.kind === "enum" ? (
        <select
          id={id}
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value === "" ? undefined : event.target.value)}
        >
          <option value="">(Default)</option>
          {prop.type.enumValues.map((entry) => (
            <option key={entry} value={entry}>
              {entry}
            </option>
          ))}
        </select>
      ) : prop.type.kind === "boolean" ? (
        <select
          id={id}
          value={value === undefined ? "" : String(value)}
          onChange={(event) => {
            const raw = event.target.value;
            onChange(raw === "" ? undefined : raw === "true");
          }}
        >
          <option value="">(Default)</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      ) : prop.type.kind === "integer" || prop.type.kind === "number" ? (
        <input
          id={id}
          type="number"
          placeholder={placeholder}
          value={typeof value === "number" ? value : ""}
          onChange={(event) => {
            const raw = event.target.value;
            onChange(raw === "" ? undefined : Number(raw));
          }}
        />
      ) : (
        <input
          id={id}
          placeholder={placeholder}
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value === "" ? undefined : event.target.value)}
        />
      )}
    </div>
  );
}

// --- Verdrahtungs-Panel -------------------------------------------------------

function WiringPanel({
  doc,
  childrenInfo,
  onDocChange,
}: InspectorProps & { doc: SpecDoc }) {
  const rules = doc.composition?.wiring ?? [];
  return (
    <div>
      <h2>Regeln</h2>
      {rules.map((rule, index) => (
        <div className="rule" key={`${rule.when}-${index}`}>
          <span>wenn {rule.when}</span>
          {rule.set ? (
            <span>
              → setze {rule.set} = {JSON.stringify(rule.to)}
            </span>
          ) : null}
          {rule.emit ? (
            <span>
              → emit {rule.emit} {rule.with ? JSON.stringify(rule.with) : ""}
            </span>
          ) : null}
          <div>
            <button
              className="small danger"
              onClick={() => onDocChange(removeWiringRule(doc, index))}
            >
              löschen
            </button>
          </div>
        </div>
      ))}
      {rules.length === 0 ? <p className="muted">Noch keine Verdrahtung.</p> : null}
      <h2 style={{ marginTop: 16 }}>Neue Regel</h2>
      <WiringForm doc={doc} childrenInfo={childrenInfo} onDocChange={onDocChange} />
    </div>
  );
}

function WiringForm({
  doc,
  childrenInfo,
  onDocChange,
}: {
  doc: SpecDoc;
  childrenInfo: Record<string, ChildInfo>;
  onDocChange: (doc: SpecDoc) => void;
}) {
  const [when, setWhen] = useState("");
  const [action, setAction] = useState<"emit" | "set">("emit");
  const [emit, setEmit] = useState("");
  const [withMapping, setWithMapping] = useState<Record<string, string>>({});
  const [setTarget, setSetTarget] = useState("");
  const [toSource, setToSource] = useState("");

  const triggerOptions = Object.entries(childrenInfo).flatMap(([alias, child]) =>
    child.api.events.map((event) => `${alias}.${event.name}`),
  );
  const ownEvents = doc.api?.events ?? [];
  const setTargets = Object.entries(childrenInfo).flatMap(([alias, child]) =>
    child.api.props.map((prop) => `${alias}.${prop.name}`),
  );

  const triggerAlias = when.split(".")[0] ?? "";
  const triggerEvent = when.split(".")[1] ?? "";
  const triggerPayloadFields =
    childrenInfo[triggerAlias]?.api.events.find((event) => event.name === triggerEvent)
      ?.payload ?? [];
  const sourceOptions = [
    ...triggerPayloadFields.map((field) => `payload.${field.name}`),
    ...Object.entries(childrenInfo).flatMap(([alias, child]) =>
      child.api.props.map((prop) => `props.${alias}.${prop.name}`),
    ),
  ];
  const selectedOwnEvent = ownEvents.find((event) => event.name === emit);
  const emitPayloadFields = Object.keys(selectedOwnEvent?.payload ?? {});

  const canSubmit =
    when !== "" &&
    ((action === "emit" && emit !== "") || (action === "set" && setTarget !== "" && toSource !== ""));

  const submit = () => {
    const rule: WiringRuleData = { when };
    if (action === "emit") {
      rule.emit = emit;
      if (emitPayloadFields.length > 0) {
        rule.with = Object.fromEntries(
          emitPayloadFields.map((field) => [field, parseSource(withMapping[field] ?? "")]),
        );
      }
    } else {
      rule.set = setTarget;
      rule.to = parseSource(toSource);
    }
    onDocChange(addWiringRule(doc, rule));
    setWhen("");
    setEmit("");
    setWithMapping({});
    setSetTarget("");
    setToSource("");
  };

  return (
    <div>
      <div className="field">
        <label htmlFor="wiring-when">wenn (Kind-Event)</label>
        <select id="wiring-when" value={when} onChange={(event) => setWhen(event.target.value)}>
          <option value="">— wählen —</option>
          {triggerOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="wiring-action">Aktion</label>
        <select
          id="wiring-action"
          value={action}
          onChange={(event) => setAction(event.target.value as "emit" | "set")}
        >
          <option value="emit">eigenes Event emittieren</option>
          <option value="set">Kind-Prop setzen</option>
        </select>
      </div>
      {action === "emit" ? (
        <>
          <div className="field">
            <label htmlFor="wiring-emit">Event (aus eigener API)</label>
            <select id="wiring-emit" value={emit} onChange={(event) => setEmit(event.target.value)}>
              <option value="">— wählen —</option>
              {ownEvents.map((event) => (
                <option key={event.name} value={event.name}>
                  {event.name}
                </option>
              ))}
            </select>
            {ownEvents.length === 0 ? (
              <span className="muted">Erst im API-Tab ein eigenes Event anlegen.</span>
            ) : null}
          </div>
          {emitPayloadFields.map((field) => (
            <div className="field" key={field}>
              <label htmlFor={`wiring-with-${field}`}>payload.{field} ←</label>
              <SourceInput
                id={`wiring-with-${field}`}
                value={withMapping[field] ?? ""}
                options={sourceOptions}
                onChange={(value) =>
                  setWithMapping((current) => ({ ...current, [field]: value }))
                }
              />
            </div>
          ))}
        </>
      ) : (
        <>
          <div className="field">
            <label htmlFor="wiring-set">setze (Kind-Prop)</label>
            <select
              id="wiring-set"
              value={setTarget}
              onChange={(event) => setSetTarget(event.target.value)}
            >
              <option value="">— wählen —</option>
              {setTargets.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="wiring-to">auf Wert</label>
            <SourceInput
              id="wiring-to"
              value={toSource}
              options={sourceOptions}
              onChange={setToSource}
            />
          </div>
        </>
      )}
      <button className="primary" disabled={!canSubmit} onClick={submit}>
        Regel hinzufügen
      </button>
    </div>
  );
}

function SourceInput({
  id,
  value,
  options,
  onChange,
}: {
  id: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <>
      <input
        id={id}
        list={`${id}-options`}
        value={value}
        placeholder="payload.…, props.…, oder Literal"
        onChange={(event) => onChange(event.target.value)}
      />
      <datalist id={`${id}-options`}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </>
  );
}

function parseSource(raw: string): unknown {
  if (raw.startsWith("payload.") || raw.startsWith("props.")) return raw;
  if (raw === "true") return true;
  if (raw === "false") return false;
  if (raw !== "" && !Number.isNaN(Number(raw))) return Number(raw);
  return raw;
}

// --- Eigene API ---------------------------------------------------------------

function OwnApiPanel({
  doc,
  childrenInfo,
  onDocChange,
}: InspectorProps & { doc: SpecDoc }) {
  const [eventName, setEventName] = useState("");
  const [payloadText, setPayloadText] = useState("");
  const [propName, setPropName] = useState("");
  const [propType, setPropType] = useState("string");
  const [propDefault, setPropDefault] = useState("");
  const [propMapTo, setPropMapTo] = useState("");

  const mapTargets = Object.entries(childrenInfo).flatMap(([alias, child]) =>
    child.api.props.map((prop) => `${alias}.${prop.name}`),
  );

  return (
    <div>
      <h2>Eigene Events</h2>
      {(doc.api?.events ?? []).map((event) => (
        <div className="rule" key={event.name}>
          <span>
            {event.name}
            {event.payload ? ` · ${JSON.stringify(event.payload)}` : ""}
          </span>
          <div>
            <button
              className="small danger"
              onClick={() => onDocChange(removeOwnEvent(doc, event.name))}
            >
              löschen
            </button>
          </div>
        </div>
      ))}
      <div className="field">
        <label htmlFor="own-event-name">Name</label>
        <input
          id="own-event-name"
          value={eventName}
          placeholder="submitted"
          onChange={(event) => setEventName(event.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="own-event-payload">Payload (feld: typ, …)</label>
        <input
          id="own-event-payload"
          value={payloadText}
          placeholder="query: string"
          onChange={(event) => setPayloadText(event.target.value)}
        />
      </div>
      <button
        disabled={eventName === ""}
        onClick={() => {
          onDocChange(upsertOwnEvent(doc, eventName, parsePayloadText(payloadText)));
          setEventName("");
          setPayloadText("");
        }}
      >
        Event speichern
      </button>

      <h2 style={{ marginTop: 20 }}>Eigene Props</h2>
      {(doc.api?.props ?? []).map((prop) => (
        <div className="rule" key={prop.name}>
          <span>
            {prop.name}: {prop.type}
            {prop.default !== undefined ? ` = ${JSON.stringify(prop.default)}` : ""}
            {prop.map_to ? ` → ${prop.map_to}` : ""}
          </span>
          <div>
            <button
              className="small danger"
              onClick={() => onDocChange(removeOwnProp(doc, prop.name))}
            >
              löschen
            </button>
          </div>
        </div>
      ))}
      <div className="field">
        <label htmlFor="own-prop-name">Name</label>
        <input
          id="own-prop-name"
          value={propName}
          placeholder="placeholder"
          onChange={(event) => setPropName(event.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="own-prop-type">Typ</label>
        <input
          id="own-prop-type"
          value={propType}
          placeholder="string | boolean | enum[a, b]"
          onChange={(event) => setPropType(event.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="own-prop-default">Default (optional)</label>
        <input
          id="own-prop-default"
          value={propDefault}
          onChange={(event) => setPropDefault(event.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="own-prop-mapto">map_to (optional, D3)</label>
        <select
          id="own-prop-mapto"
          value={propMapTo}
          onChange={(event) => setPropMapTo(event.target.value)}
        >
          <option value="">— kein Forwarding —</option>
          {mapTargets.map((target) => (
            <option key={target} value={target}>
              {target}
            </option>
          ))}
        </select>
      </div>
      <button
        disabled={propName === "" || propType === ""}
        onClick={() => {
          onDocChange(
            upsertOwnProp(doc, {
              name: propName,
              type: propType,
              default: propDefault === "" ? undefined : parseSource(propDefault),
              map_to: propMapTo === "" ? undefined : propMapTo,
            }),
          );
          setPropName("");
          setPropDefault("");
          setPropMapTo("");
        }}
      >
        Prop speichern
      </button>
    </div>
  );
}

function parsePayloadText(text: string): Record<string, string> {
  const payload: Record<string, string> = {};
  for (const part of text.split(",")) {
    const [name, type] = part.split(":").map((entry) => entry.trim());
    if (name && type) payload[name] = type;
  }
  return payload;
}

// --- Spec-Meta ----------------------------------------------------------------

function SpecPanel({ doc, onDocChange }: InspectorProps & { doc: SpecDoc }) {
  const name = doc.id.split("/")[1] ?? "";
  return (
    <div>
      <h2>Spec</h2>
      <div className="field">
        <label htmlFor="spec-name">Name (@org/…)</label>
        <input
          id="spec-name"
          value={name}
          onChange={(event) => onDocChange(renameSpec(doc, event.target.value))}
        />
      </div>
      <div className="field">
        <label htmlFor="spec-version">Version</label>
        <input
          id="spec-version"
          value={doc.version}
          onChange={(event) => onDocChange({ ...doc, version: event.target.value })}
        />
      </div>
      <div className="field">
        <label htmlFor="spec-kind">Kind</label>
        <select
          id="spec-kind"
          value={doc.kind}
          onChange={(event) => onDocChange({ ...doc, kind: event.target.value })}
        >
          <option value="ui-component">ui-component (Composite)</option>
          <option value="app">app</option>
          <option value="screen">screen</option>
          <option value="workflow">workflow</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="spec-summary">Summary</label>
        <textarea
          id="spec-summary"
          value={doc.summary}
          rows={3}
          onChange={(event) => onDocChange({ ...doc, summary: event.target.value })}
        />
      </div>
    </div>
  );
}
