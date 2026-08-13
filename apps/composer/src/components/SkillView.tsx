import Markdown from "react-markdown";

import { describeAge, isStale } from "../age";
import type { Selection, SkillDetail } from "../types";
import { StepFlow } from "./StepFlow";

interface Props {
  skill: SkillDetail | null;
  selection: Selection;
  fileContent: string | null;
  onSelect: (selection: Selection) => void;
  onOpenChild: (source: string) => void;
}

function isSelected(selection: Selection, kind: Selection["kind"], id?: string): boolean {
  if (selection.kind !== kind) return false;
  if (kind === "step") return (selection as { title: string }).title === id;
  if (kind === "source") return (selection as { url: string }).url === id;
  if (kind === "file") return (selection as { path: string }).path === id;
  return true;
}

/**
 * Read-only view of a skill. Clicking anywhere sets the selection — that is
 * what a context-aware agent reads to know what the question is about.
 *
 * The body is rendered as one document rather than chopped into cards: a skill
 * *is* markdown, and pulling it apart would show something the agent never
 * sees. The inferred structure sits beside it as navigation.
 */
export function SkillView({ skill, selection, fileContent, onSelect, onOpenChild }: Props) {
  if (!skill) {
    return (
      <main className="view">
        <div className="empty">Pick a skill on the left.</div>
      </main>
    );
  }

  return (
    <main className="view">
      <section
        className={`card${isSelected(selection, "skill") ? " selected" : ""}`}
        onClick={() => onSelect({ kind: "skill" })}
      >
        <h2>{skill.name}</h2>
        {/* The description is the only thing an agent sees before loading the
            skill, so it gets the prominent spot. */}
        <p>{skill.description}</p>
        {skill.deprecated ? (
          <p className="stale-note">
            Withdrawn by its author: {skill.deprecated}
            {skill.superseded_by ? ` — use ${skill.superseded_by}` : ""}
          </p>
        ) : null}
        {skill.compatibility ? <p className="muted">{skill.compatibility}</p> : null}
        {skill.stack.length > 0 || skill.platforms.length > 0 ? (
          <span className="axes">
            {[...skill.stack, ...skill.platforms].map((term) => (
              <span key={term} className="axis">
                {term}
              </span>
            ))}
          </span>
        ) : null}
        {skill.uses.map((used) => (
          <p key={used}>
            builds on{" "}
            <button className="link" onClick={() => onOpenChild(used)}>
              {used}
            </button>
          </p>
        ))}
      </section>

      {skill.steps.length > 0 ? (
        <>
          <h3 className="section-title">Steps</h3>
          <div className="flow-and-steps">
            <StepFlow
              steps={skill.steps}
              selection={selection}
              onSelect={(title) => onSelect({ kind: "step", title })}
            />
            <ul className="steps plain">
              {skill.steps.map((step) => (
                <li key={step.title}>
                  <button
                    className={`chip${isSelected(selection, "step", step.title) ? " selected" : ""}`}
                    onClick={() => onSelect({ kind: "step", title: step.title })}
                  >
                    {step.number !== null ? `${step.number}. ` : ""}
                    {step.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      ) : null}

      <section className="card">
        <h3>SKILL.md</h3>
        <div className="detail markdown">
          <Markdown>{skill.markdown}</Markdown>
        </div>
      </section>

      {skill.sources.length > 0 ? (
        <section className="card">
          <h3>Sources</h3>
          {skill.sources.map((source) => (
            <button
              key={source.url}
              className={`chip${isStale(source.retrieved ?? "") ? " stale" : ""}${
                isSelected(selection, "source", source.url) ? " selected" : ""
              }`}
              title={source.url}
              onClick={() => onSelect({ kind: "source", url: source.url })}
            >
              {source.title} ({source.retrieved ? describeAge(source.retrieved) : "no date"})
            </button>
          ))}
        </section>
      ) : null}

      {skill.files.length > 0 ? (
        <section className="card">
          <h3>Bundled files</h3>
          {skill.files.map((path) => (
            <button
              key={path}
              className={`chip${isSelected(selection, "file", path) ? " selected" : ""}`}
              onClick={() => onSelect({ kind: "file", path })}
            >
              {path}
            </button>
          ))}
          {fileContent !== null ? (
            <div className="asset-view">
              <pre>{fileContent}</pre>
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
