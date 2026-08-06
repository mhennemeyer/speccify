import { useMemo } from "react";

import type { Proposal } from "../api";

interface Props {
  proposal: Proposal;
  currentYaml: string;
  onApply: () => void;
  onDiscard: () => void;
}

interface DiffLine {
  kind: "same" | "added" | "removed";
  text: string;
}

/**
 * Line diff, longest-common-subsequence style. Small enough to hand-roll:
 * playbooks are hundreds of lines, and a diff library for one panel would be
 * a dependency that has to be kept current for the rest of the app's life.
 */
function diff(before: string, after: string): DiffLine[] {
  const a = before.split("\n");
  const b = after.split("\n");
  const table: number[][] = Array.from({ length: a.length + 1 }, () =>
    new Array<number>(b.length + 1).fill(0),
  );
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }
  const lines: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      lines.push({ kind: "same", text: a[i] });
      i += 1;
      j += 1;
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      lines.push({ kind: "removed", text: a[i] });
      i += 1;
    } else {
      lines.push({ kind: "added", text: b[j] });
      j += 1;
    }
  }
  while (i < a.length) {
    lines.push({ kind: "removed", text: a[i] });
    i += 1;
  }
  while (j < b.length) {
    lines.push({ kind: "added", text: b[j] });
    j += 1;
  }
  return lines;
}

/** Only the changed regions, with a little context around them. */
function condense(lines: DiffLine[], context = 2): DiffLine[] {
  const keep = new Set<number>();
  lines.forEach((line, index) => {
    if (line.kind === "same") return;
    for (let offset = -context; offset <= context; offset += 1) {
      const target = index + offset;
      if (target >= 0 && target < lines.length) keep.add(target);
    }
  });
  const out: DiffLine[] = [];
  let skipped = false;
  lines.forEach((line, index) => {
    if (keep.has(index)) {
      if (skipped) out.push({ kind: "same", text: "…" });
      skipped = false;
      out.push(line);
    } else {
      skipped = true;
    }
  });
  return out;
}

export function ProposalPanel({ proposal, currentYaml, onApply, onDiscard }: Props) {
  const lines = useMemo(
    () => condense(diff(currentYaml, proposal.playbook_yaml)),
    [currentYaml, proposal.playbook_yaml],
  );
  const changed = lines.filter((line) => line.kind !== "same").length;

  return (
    <section className="card proposal">
      <h3>The agent proposes a change</h3>
      {proposal.rationale ? <p>{proposal.rationale}</p> : null}
      <p className="muted">{changed} changed line(s) in {proposal.source}</p>
      <pre className="diff">
        {lines.map((line, index) => (
          <div key={index} className={`diff-line ${line.kind}`}>
            {line.kind === "added" ? "+" : line.kind === "removed" ? "-" : " "} {line.text}
          </div>
        ))}
      </pre>
      <div className="row">
        <button className="primary" onClick={onApply}>
          Apply
        </button>
        <button onClick={onDiscard}>Discard</button>
      </div>
    </section>
  );
}
