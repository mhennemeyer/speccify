import { useCallback, useEffect, useState } from "react";

import { ApiError, getAsset, getPlaybook, listPlaybooks, searchIndex } from "./api";
import { PlaybookView } from "./components/PlaybookView";
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
        <PlaybookView
          playbook={detail}
          selection={selection}
          assetContent={assetContent}
          onSelect={(next) => void select(next)}
          onOpenChild={(source) => void open(source)}
        />
      </div>
    </>
  );
}
