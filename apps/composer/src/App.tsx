import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  applyProposal,
  discardProposal,
  getFile,
  getSkill,
  getProposal,
  listSkills,
  pushSelection,
  searchIndex,
  type Proposal,
} from "./api";
import { SkillView } from "./components/SkillView";
import { ProposalPanel } from "./components/ProposalPanel";
import { SkillList } from "./components/SkillList";
import type { IndexHit, Selection, SkillDetail, SkillSummary } from "./types";

/**
 * The viewer: read a skill, click into it, ask an agent about what you
 * clicked. There is deliberately no edit mode — changes come from the agent as
 * a proposal, the YAML pane is the escape hatch.
 */
export function App() {
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [selection, setSelection] = useState<Selection>({ kind: "skill" });
  const [assetContent, setAssetContent] = useState<string | null>(null);
  const [indexHits, setIndexHits] = useState<IndexHit[]>([]);
  const [indexStatus, setIndexStatus] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        setSkills(await listSkills());
      } catch (error) {
        setStatus(`Could not load skills: ${String(error)}`);
      }
    })();
  }, []);

  const open = useCallback(async (source: string) => {
    try {
      const loaded = await getSkill(source);
      setDetail(loaded);
      setSelection({ kind: "skill" });
      setAssetContent(null);
      setStatus(`${loaded.id}@${loaded.version} loaded.`);
      void pushSelection({ source: loaded.source, kind: "skill" }).catch(() => undefined);
    } catch (error) {
      setStatus(
        error instanceof ApiError && error.status === 404
          ? `Not found: ${source}`
          : `Could not open ${source}: ${String(error)}`,
      );
    }
  }, []);

  const searchTheIndex = useCallback(async (query: string) => {
    setIndexStatus("Searching…");
    try {
      const hits = await searchIndex(query);
      setIndexHits(hits);
      setIndexStatus(hits.length === 0 ? "No hits in the index." : "");
    } catch (error) {
      setIndexHits([]);
      setIndexStatus(
        error instanceof ApiError && error.status === 404
          ? "No index configured (SPECCIFY_INDEX)."
          : `Index error: ${String(error)}`,
      );
    }
  }, []);

  const select = useCallback(
    async (next: Selection) => {
      setSelection(next);
      setAssetContent(null);
      // Tell the backend what is selected: the agent next door reads it.
      if (detail) {
        void pushSelection({
          source: detail.source,
          kind: next.kind,
          step_title: next.kind === "step" ? next.title : undefined,
          source_url: next.kind === "source" ? next.url : undefined,
          file_path: next.kind === "file" ? next.path : undefined,
        }).catch(() => undefined);
      }
      if (next.kind === "file" && detail) {
        try {
          const file = await getFile(detail.source, next.path);
          setAssetContent(
            file.encoding === "utf-8" ? file.content : "(binary file — download to inspect)",
          );
        } catch (error) {
          setAssetContent(`Could not load file: ${String(error)}`);
        }
      }
    },
    [detail],
  );

  // An agent can propose a change at any time; poll for it rather than making
  // the user reload.
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const pending = await getProposal();
        if (!cancelled) setProposal(pending);
      } catch {
        /* backend not up yet — try again on the next tick */
      }
    };
    void tick();
    const timer = window.setInterval(() => void tick(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const acceptProposal = useCallback(async () => {
    try {
      const applied = await applyProposal();
      setProposal(null);
      setStatus(`Applied — ${applied.path}`);
      if (detail) setDetail(await getSkill(detail.source));
      setSkills(await listSkills());
    } catch (error) {
      setStatus(`Could not apply: ${String(error)}`);
    }
  }, [detail]);

  const rejectProposal = useCallback(async () => {
    await discardProposal().catch(() => undefined);
    setProposal(null);
    setStatus("Proposal discarded.");
  }, []);

  return (
    <>
      <header className="topbar">
        <h1>Speccify</h1>
        {detail ? (
          <span className="badge accent">
            {detail.id}@{detail.version}
          </span>
        ) : (
          <span className="muted">no skill open</span>
        )}
        <div className="spacer" />
        <span className="muted">{status}</span>
      </header>
      <div className="layout">
        <SkillList
          skills={skills}
          indexHits={indexHits}
          indexStatus={indexStatus}
          activeSource={detail?.source ?? null}
          onOpen={(source) => void open(source)}
          onSearchIndex={(query) => void searchTheIndex(query)}
        />
        <div className="main">
          {proposal && detail && proposal.source === detail.source ? (
            <ProposalPanel
              proposal={proposal}
              current={detail.raw}
              onApply={() => void acceptProposal()}
              onDiscard={() => void rejectProposal()}
            />
          ) : null}
          <SkillView
            skill={detail}
            selection={selection}
            fileContent={assetContent}
            onSelect={(next) => void select(next)}
            onOpenChild={(source) => void open(source)}
          />
        </div>
      </div>
    </>
  );
}
