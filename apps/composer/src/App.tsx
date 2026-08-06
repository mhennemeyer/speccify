import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  applyProposal,
  discardProposal,
  getAsset,
  getPlaybook,
  getProposal,
  listPlaybooks,
  pushSelection,
  searchIndex,
  type Proposal,
} from "./api";
import { PlaybookView } from "./components/PlaybookView";
import { ProposalPanel } from "./components/ProposalPanel";
import { PlaybookList } from "./components/PlaybookList";
import type { IndexHit, PlaybookDetail, PlaybookSummary, Selection } from "./types";

/**
 * The viewer: read a playbook, click into it, ask an agent about what you
 * clicked. There is deliberately no edit mode — changes come from the agent as
 * a proposal, the YAML pane is the escape hatch.
 */
export function App() {
  const [playbooks, setPlaybooks] = useState<PlaybookSummary[]>([]);
  const [detail, setDetail] = useState<PlaybookDetail | null>(null);
  const [selection, setSelection] = useState<Selection>({ kind: "playbook" });
  const [assetContent, setAssetContent] = useState<string | null>(null);
  const [indexHits, setIndexHits] = useState<IndexHit[]>([]);
  const [indexStatus, setIndexStatus] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        setPlaybooks(await listPlaybooks());
      } catch (error) {
        setStatus(`Could not load playbooks: ${String(error)}`);
      }
    })();
  }, []);

  const open = useCallback(async (source: string) => {
    try {
      const loaded = await getPlaybook(source);
      setDetail(loaded);
      setSelection({ kind: "playbook" });
      setAssetContent(null);
      setStatus(`${loaded.id}@${loaded.version} loaded.`);
      void pushSelection({ source: loaded.source, kind: "playbook" }).catch(() => undefined);
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
      if (next.kind === "step") {
        document
          .getElementById(`step-${next.stepId}`)
          ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
      // Tell the backend what is selected: the agent next door reads it.
      if (detail) {
        void pushSelection({
          source: detail.source,
          kind: next.kind,
          step_id: next.kind === "step" ? next.stepId : undefined,
          source_id: next.kind === "source" ? next.sourceId : undefined,
          asset_path: next.kind === "asset" ? next.path : undefined,
        }).catch(() => undefined);
      }
      if (next.kind === "asset" && detail) {
        try {
          const asset = await getAsset(detail.source, next.path);
          setAssetContent(
            asset.encoding === "utf-8" ? asset.content : "(binary asset — download to inspect)",
          );
        } catch (error) {
          setAssetContent(`Could not load asset: ${String(error)}`);
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
      if (detail) setDetail(await getPlaybook(detail.source));
      setPlaybooks(await listPlaybooks());
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
          <span className="muted">no playbook open</span>
        )}
        <div className="spacer" />
        <span className="muted">{status}</span>
      </header>
      <div className="layout">
        <PlaybookList
          playbooks={playbooks}
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
              currentYaml={detail.yaml}
              onApply={() => void acceptProposal()}
              onDiscard={() => void rejectProposal()}
            />
          ) : null}
          <PlaybookView
            playbook={detail}
          selection={selection}
          assetContent={assetContent}
            onSelect={(next) => void select(next)}
            onOpenChild={(source) => void open(source)}
          />
        </div>
      </div>
    </>
  );
}
