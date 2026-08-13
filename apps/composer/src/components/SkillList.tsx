import { useMemo, useState } from "react";

import type { IndexHit, SkillSummary } from "../types";

interface Props {
  skills: SkillSummary[];
  indexHits: IndexHit[];
  indexStatus: string;
  activeSource: string | null;
  onOpen: (source: string) => void;
  onSearchIndex: (query: string) => void;
}

function matches(skill: SkillSummary, needle: string): boolean {
  if (!needle) return true;
  return [
    skill.name,
    skill.id,
    skill.description,
    ...skill.platforms,
    ...skill.stack,
  ]
    .join(" ")
    .toLowerCase()
    .includes(needle);
}

export function SkillList({
  skills,
  indexHits,
  indexStatus,
  activeSource,
  onOpen,
  onSearchIndex,
}: Props) {
  const [filter, setFilter] = useState("");
  const needle = filter.trim().toLowerCase();
  const visible = useMemo(
    () => skills.filter((skill) => matches(skill, needle)),
    [skills, needle],
  );

  return (
    <aside className="library">
      <h2>Skills</h2>
      <input
        id="library-filter"
        className="filter"
        value={filter}
        placeholder="Filter by title, stack, platform, keyword…"
        onChange={(event) => setFilter(event.target.value)}
      />
      {visible.map((skill) => (
        <button
          key={skill.source}
          className={`library-item${skill.source === activeSource ? " active" : ""}`}
          onClick={() => onOpen(skill.source)}
        >
          <strong>{skill.name}</strong>
          <span className="meta">
            {skill.id}@{skill.version} · {skill.steps} steps
          </span>
          <span className="muted">{skill.description}</span>
          {skill.stack.length > 0 || skill.platforms.length > 0 ? (
            <span className="axes">
              {[...skill.stack, ...skill.platforms].map((term) => (
                <span key={term} className="axis">
                  {term}
                </span>
              ))}
            </span>
          ) : null}
          {null}
        </button>
      ))}
      {skills.length === 0 ? (
        <p className="muted">No skills in the library — is the backend running?</p>
      ) : null}
      {skills.length > 0 && visible.length === 0 ? (
        <p className="muted">Nothing matches “{filter}”.</p>
      ) : null}

      {/* Discovery: skills that are not in this library at all. */}
      <h2 className="index-heading">Index</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSearchIndex(filter);
        }}
      >
        <button className="small" type="submit">
          Search the index for “{filter || "everything"}”
        </button>
      </form>
      {indexStatus ? <p className="muted">{indexStatus}</p> : null}
      {indexHits.map((hit) => (
        <button
          key={hit.source}
          className={`library-item index-item${hit.source === activeSource ? " active" : ""}`}
          onClick={() => onOpen(hit.source)}
        >
          <strong>{hit.title}</strong>
          <span className="meta">{hit.source}</span>
          <span className="muted">{hit.summary}</span>
        </button>
      ))}
    </aside>
  );
}
