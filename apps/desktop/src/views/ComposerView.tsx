// Composer-Einstieg (Plan desktop-app-und-composer.md, A1): öffnet pro Klick
// ein Composer-Fenster — die App spawnt dafür ein eigenes speccify-web-backend
// (freier Port, Supervisor) und lädt die unter /ui mitservierte SPA.

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ActionButton, ErrorBox } from "../components/ui";

const REPO_KEY = "speccify.repoPath";
const DEFAULT_REPO = "~/Desktop/Work/speccify";

export default function ComposerView() {
  const [repo, setRepo] = useState(
    () => localStorage.getItem(REPO_KEY) ?? DEFAULT_REPO,
  );
  const [error, setError] = useState<string | null>(null);
  const [opened, setOpened] = useState<string[]>([]);

  const openWindow = async () => {
    localStorage.setItem(REPO_KEY, repo);
    setError(null);
    try {
      const url = await invoke<string>("open_composer", { repo });
      setOpened((urls) => [...urls, url]);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <p className="text-sm text-slate-600">
        Öffnet den visuellen Composer in einem eigenen Fenster. Die App startet
        dafür ein <code>speccify-web-backend</code> auf einem freien Port
        (Fenster schließen beendet es wieder). Voraussetzung im Repo:
        einmal <code>uv sync</code> und <code>pnpm run composer:build</code>.
      </p>
      <div>
        <label
          htmlFor="composer-repo"
          className="mb-1 block text-xs font-medium text-slate-500"
        >
          Speccify-Repo
        </label>
        <input
          id="composer-repo"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
          spellCheck={false}
        />
      </div>
      <ActionButton
        onClick={openWindow}
        className="bg-slate-800 text-white hover:bg-slate-700"
      >
        Composer-Fenster öffnen
      </ActionButton>
      {error ? <ErrorBox message={error} /> : null}
      {opened.length > 0 ? (
        <div className="text-xs text-slate-500">
          Geöffnet: {opened.join(" · ")}
        </div>
      ) : null}
    </div>
  );
}
