import { useMemo, useState } from "react";

import type { IndexHit, PlaybookSummary } from "../types";

interface Props {
  playbooks: PlaybookSummary[];
  indexHits: IndexHit[];
  indexStatus: string;
  activeSource: string | null;
  onOpen: (source: string) => void;
  onSearchIndex: (query: string) => void;
}

function matches(playbook: PlaybookSummary, needle: string): boolean {
  if (!needle) return true;
  return [
    playbook.title,
    playbook.id,
    playbook.summary,
    ...playbook.keywords,
    ...playbook.platforms,
    ...playbook.stack,
  ]
    .join(" ")
    .toLowerCase()
    .includes(needle);
}

export function PlaybookList({
  playbooks,
  indexHits,
  indexStatus,
  activeSource,
  onOpen,
  onSearchIndex,
}: Props) {
  const [filter, setFilter] = useState("");
  const needle = filter.trim().toLowerCase();
  const visible = useMemo(
    () => playbooks.filter((playbook) => matches(playbook, needle)),
    [playbooks, needle],
  );

  return (
    <aside className="library">
      <h2>Playbooks</h2>
      <input
        id="library-filter"
        className="filter"
        value={filter}
        placeholder="Filter by title, stack, platform, keyword…"
        onChange={(event) => setFilter(event.target.value)}
      />
      {visible.map((playbook) => (
        <button
          key={playbook.source}
          className={`library-item${playbook.source === activeSource ? " active" : ""}`}
          onClick={() => onOpen(playbook.source)}
        >
          <strong>{playbook.title}</strong>
          <span className="meta">
            {playbook.id}@{playbook.version} · {playbook.steps} steps
          </span>
          <span className="muted">{playbook.summary}</span>
          {playbook.stack.length > 0 || playbook.platforms.length > 0 ? (
            <span className="axes">
              {[...playbook.stack, ...playbook.platforms].map((term) => (
                <span key={term} className="axis">
                  {term}
                </span>
              ))}
            </span>
          ) : null}
          {playbook.keywords.length > 0 ? (
            <span className="keywords">{playbook.keywords.join(" · ")}</span>
          ) : null}
        </button>
      ))}
      {playbooks.length === 0 ? (
        <p className="muted">No playbooks in the library — is the backend running?</p>
      ) : null}
      {playbooks.length > 0 && visible.length === 0 ? (
        <p className="muted">Nothing matches “{filter}”.</p>
      ) : null}

      {/* Discovery: playbooks that are not in this library at all. */}
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
