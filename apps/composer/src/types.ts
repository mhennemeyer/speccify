// Typen für die Composer-UI — spiegeln die JSON-Contracts des Backends
// (`services/composer.py::api_contract_dict` + Routen-Responses).

export interface TypeInfo {
  raw: string;
  kind: "string" | "integer" | "number" | "boolean" | "enum" | "other";
  enumValues: string[];
}

export interface PropContract {
  name: string;
  type: TypeInfo;
  required: boolean;
  default: unknown;
  hasDefault: boolean;
  description: string;
  constraints: string[];
  mapTo: string | null;
}

export interface PayloadField {
  name: string;
  type: TypeInfo;
}

export interface EventContract {
  name: string;
  payload: PayloadField[];
  description: string;
}

export interface SlotContract {
  name: string;
  optional: boolean;
  description: string;
}

export interface ApiContract {
  props: PropContract[];
  events: EventContract[];
  slots: SlotContract[];
  fixtures: { name: string; data: unknown; description: string }[];
  outputs: { name: string; type: TypeInfo }[];
}

export interface SpecSummary {
  id: string;
  version: string;
  title: string;
  yaml: string;
}

export interface ChildInfo {
  id: string;
  version: string;
  kind: string;
  title: string;
  api: ApiContract;
}

export interface SpecDetail {
  id: string;
  version: string;
  versions: string[];
  kind: string;
  title: string;
  summary: string;
  yaml: string;
  api: ApiContract;
  composition: CompositionData | null;
  children: Record<string, ChildInfo>;
}

// --- Editierbares Dokument (spiegelt die Spec-YAML-Struktur) -----------------

export interface TreeNodeData {
  node: string;
  props?: Record<string, unknown>;
  slots?: Record<string, TreeNodeData[]>;
}

export interface WiringRuleData {
  when: string;
  emit?: string;
  with?: Record<string, unknown>;
  set?: string;
  to?: unknown;
}

export interface CompositionData {
  uses: Record<string, string>;
  tree: TreeNodeData[];
  wiring?: WiringRuleData[];
}

export interface OwnPropData {
  name: string;
  type: string;
  required?: boolean;
  default?: unknown;
  map_to?: string;
}

export interface OwnEventData {
  name: string;
  payload?: Record<string, string>;
}

export interface SpecDoc {
  schema_version: 1;
  id: string;
  version: string;
  kind: string;
  title: string;
  summary: string;
  license?: string;
  api?: {
    props?: OwnPropData[];
    events?: OwnEventData[];
  };
  composition?: CompositionData;
}

export interface ValidationIssue {
  path: string;
  message: string;
  source: string;
}

export interface LogEntry {
  kind: "emit" | "set" | "trigger" | "info";
  text: string;
}
