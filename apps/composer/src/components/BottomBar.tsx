import { useEffect, useState } from "react";

import { docToYaml } from "../doc";
import type { LogEntry, SpecDoc, ValidationIssue } from "../types";

interface BottomBarProps {
  doc: SpecDoc | null;
  issues: ValidationIssue[] | null;
  eventLog: LogEntry[];
  onApplyYaml: (yamlText: string) => void;
  onResetSim: () => void;
}

export function BottomBar({ doc, issues, eventLog, onApplyYaml, onResetSim }: BottomBarProps) {
  const generated = doc ? docToYaml(doc) : "";
  const [draft, setDraft] = useState(generated);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!dirty) setDraft(generated);
  }, [generated, dirty]);

  return (
    <footer className="bottombar">
      <section>
        <h2>
          Spec-YAML (Round-Trip){" "}
          {dirty ? (
            <button
              className="small primary"
              onClick={() => {
                onApplyYaml(draft);
                setDirty(false);
              }}
            >
              übernehmen
            </button>
          ) : null}
          {dirty ? (
            <button className="small" onClick={() => setDirty(false)}>
              verwerfen
            </button>
          ) : null}
        </h2>
        <textarea
          className="yaml"
          value={draft}
          spellCheck={false}
          onChange={(event) => {
            setDraft(event.target.value);
            setDirty(true);
          }}
        />
        {issues !== null ? (
          issues.length === 0 ? (
            <p className="ok">✓ Schema + Komposition sauber.</p>
          ) : (
            issues.map((issue, index) => (
              <p className="issue" key={index}>
                [{issue.source}] {issue.path}: {issue.message}
              </p>
            ))
          )
        ) : null}
      </section>
      <section>
        <h2>
          Event-Log{" "}
          <button className="small" onClick={onResetSim}>
            Simulation zurücksetzen
          </button>
        </h2>
        {eventLog.length === 0 ? (
          <p className="muted">Event-Chips im Canvas anklicken — hier erscheinen Trigger, set-Effekte und emittierte Events.</p>
        ) : null}
        {eventLog.map((entry, index) => (
          <div className={`log-entry ${entry.kind}`} key={index}>
            {entry.text}
          </div>
        ))}
      </section>
    </footer>
  );
}
