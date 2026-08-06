import type { PlaybookDetail, Selection } from "../types";

interface Props {
  playbook: PlaybookDetail | null;
  selection: Selection;
  assetContent: string | null;
  onSelect: (selection: Selection) => void;
  onOpenChild: (source: string) => void;
}

function isSelected(selection: Selection, kind: Selection["kind"], id?: string): boolean {
  if (selection.kind !== kind) return false;
  if (kind === "step") return (selection as { stepId: string }).stepId === id;
  if (kind === "source") return (selection as { sourceId: string }).sourceId === id;
  if (kind === "asset") return (selection as { path: string }).path === id;
  return true;
}

/**
 * Read-only view of a playbook. Clicking anywhere sets the selection — that is
 * what a context-aware agent reads to know what the question is about.
 */
export function PlaybookView({
  playbook,
  selection,
  assetContent,
  onSelect,
  onOpenChild,
}: Props) {
  if (!playbook) {
    return (
      <main className="view">
        <div className="empty">Pick a playbook on the left.</div>
      </main>
    );
  }

  return (
    <main className="view">
      <section
        className={`card${isSelected(selection, "playbook") ? " selected" : ""}`}
        onClick={() => onSelect({ kind: "playbook" })}
      >
        <h2>{playbook.title}</h2>
        <p>{playbook.summary}</p>
        {playbook.applies_to.platforms.length > 0 ? (
          <p className="muted">platforms: {playbook.applies_to.platforms.join(", ")}</p>
        ) : null}
        {playbook.applies_to.requires.length > 0 ? (
          <ul className="plain">
            {playbook.applies_to.requires.map((item) => (
              <li key={item}>requires: {item}</li>
            ))}
          </ul>
        ) : null}
        {playbook.prerequisites.length > 0 ? (
          <>
            <h3>Prerequisites</h3>
            <ul>
              {playbook.prerequisites.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      <h3 className="section-title">Steps</h3>
      <ol className="steps">
        {playbook.steps.map((step, index) => (
          <li key={step.id}>
            <section
              className={`card step${isSelected(selection, "step", step.id) ? " selected" : ""}`}
              onClick={() => onSelect({ kind: "step", stepId: step.id })}
            >
              <h4>
                <span className="step-number">{index + 1}</span> {step.title}
                <span className="badge">{step.id}</span>
              </h4>
              {step.uses ? (
                <p>
                  delegates to{" "}
                  <button
                    className="link"
                    onClick={(event) => {
                      event.stopPropagation();
                      onOpenChild(step.uses!.replace(/@[\^~]?[\d.]+$/, ""));
                    }}
                  >
                    {step.uses}
                  </button>
                </p>
              ) : (
                <pre className="detail">{step.detail}</pre>
              )}
              {step.verify ? <p className="verify">verify: {step.verify}</p> : null}
              {step.sources.map((source) => (
                <button
                  key={source.id}
                  className={`chip${isSelected(selection, "source", source.id) ? " selected" : ""}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect({ kind: "source", sourceId: source.id });
                  }}
                >
                  {source.title} ({source.retrieved})
                </button>
              ))}
              {step.assets.map((asset) => (
                <button
                  key={asset}
                  className={`chip${isSelected(selection, "asset", asset) ? " selected" : ""}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect({ kind: "asset", path: asset });
                  }}
                >
                  {asset}
                </button>
              ))}
            </section>
          </li>
        ))}
      </ol>

      {assetContent !== null ? (
        <section className="card asset-view">
          <h3>Asset</h3>
          <pre className="detail">{assetContent}</pre>
        </section>
      ) : null}

      {playbook.pitfalls.length > 0 ? (
        <section className="card pitfalls">
          <h3>Pitfalls</h3>
          <ul>
            {playbook.pitfalls.map((pitfall) => (
              <li key={pitfall}>{pitfall}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="card">
        <h3>Sources</h3>
        <ul className="plain">
          {playbook.sources.map((source) => (
            <li key={source.id}>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.title}
              </a>{" "}
              <span className="muted">retrieved {source.retrieved}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
