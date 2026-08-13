// Types mirroring the backend's JSON (routes/playbooks.py, routes/session.py).

export interface SourceRef {
  title: string;
  url: string;
  retrieved: string | null;
}

/** A `##` section of the body. Inferred, never declared — the spec puts no
 *  requirements on a skill's markdown. */
export interface SkillStep {
  number: number | null;
  title: string;
  verify: string | null;
}

export interface SkillSummary {
  id: string;
  name: string;
  source: string;
  version: string;
  description: string;
  stack: string[];
  platforms: string[];
  uses: string[];
  deprecated: string | null;
  steps: number;
}

export interface SkillDetail {
  id: string;
  name: string;
  source: string;
  version: string | null;
  description: string;
  license: string | null;
  compatibility: string | null;
  stack: string[];
  platforms: string[];
  uses: string[];
  deprecated: string | null;
  superseded_by: string | null;
  /** The skill itself — what an agent would follow. */
  markdown: string;
  steps: SkillStep[];
  sources: SourceRef[];
  files: string[];
  /** The raw SKILL.md, so a proposal can be diffed against it. */
  raw: string;
}

/** What the user selected in the viewer — the context an agent asks about. */
export type Selection =
  | { kind: "skill" }
  | { kind: "step"; title: string }
  | { kind: "source"; url: string }
  | { kind: "file"; path: string };

/** A hit from a discovery index (`GET /api/v1/index`). */
export interface IndexHit {
  source: string;
  title: string;
  summary: string;
  platforms: string[];
  stack: string[];
  keywords: string[];
  homepage: string | null;
  license: string | null;
  origin: string;
}
