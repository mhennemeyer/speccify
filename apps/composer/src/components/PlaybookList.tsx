import type { PlaybookSummary } from "../types";

interface Props {
  playbooks: PlaybookSummary[];
  activeSource: string | null;
  onOpen: (source: string) => void;
}

export function PlaybookList({ playbooks, activeSource, onOpen }: Props) {
  return (
    <aside className="library">
      <h2>Playbooks</h2>
      {playbooks.map((playbook) => (
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
          {playbook.keywords.length > 0 ? (
            <span className="keywords">{playbook.keywords.join(" · ")}</span>
          ) : null}
        </button>
      ))}
      {playbooks.length === 0 ? (
        <p className="muted">No playbooks in the library — is the backend running?</p>
      ) : null}
    </aside>
  );
}
