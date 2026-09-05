// Icons der Navigator-Tab-Leiste (W7, Vorbild iKanban `SidebarTabBar`):
// schlichte 16-px-Strichzeichnungen, ohne Icon-Bibliothek.

import type { ReactElement } from "react";

const PATHS: Record<string, ReactElement> = {
  board: (
    <>
      <rect x="2" y="3" width="3.5" height="10" rx="0.8" />
      <rect x="6.25" y="3" width="3.5" height="7" rx="0.8" />
      <rect x="10.5" y="3" width="3.5" height="4.5" rx="0.8" />
    </>
  ),
  playbooks: (
    <>
      <path d="M3 2.5h7.5a1.5 1.5 0 0 1 1.5 1.5v9.5H4.5A1.5 1.5 0 0 1 3 12V2.5z" />
      <path d="M3 12a1.5 1.5 0 0 1 1.5-1.5H12" />
      <path d="M6 5.5h3.5" />
    </>
  ),
  plans: (
    <>
      <path d="M3 4h10M3 8h10M3 12h6" />
      <path d="M11 11l1.5 1.5L15 10" />
    </>
  ),
  skills: (
    <>
      <path d="M8 2.5l1.3 3.2 3.2 1.3-3.2 1.3L8 11.5 6.7 8.3 3.5 7l3.2-1.3z" />
      <path d="M12.5 11.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z" />
    </>
  ),
  // Gruppe „Orga" (Pläne, Playbooks, Skills): gestapelte Ebenen
  orga: (
    <>
      <path d="M8 2.5l6 3-6 3-6-3z" />
      <path d="M2 8.5l6 3 6-3" />
      <path d="M2 11.5l6 3 6-3" />
    </>
  ),
  // Gruppe „Technik" (Tools, Aktionen, MCPs, Agent)
  technik: (
    <>
      <path d="M10.5 2.5a3 3 0 0 0-3.9 3.9L2.5 10.5l3 3 4.1-4.1a3 3 0 0 0 3.9-3.9l-2 2-2-2z" />
    </>
  ),
  tools: (
    <>
      <path d="M10.5 2.5a3 3 0 0 0-3.9 3.9L2.5 10.5l3 3 4.1-4.1a3 3 0 0 0 3.9-3.9l-2 2-2-2z" />
    </>
  ),
  actions: (
    <>
      <path d="M4.5 3v10l8-5z" />
    </>
  ),
  mcps: (
    <>
      <path d="M6 2.5v3M10 2.5v3" />
      <path d="M4 5.5h8v2a4 4 0 0 1-8 0z" />
      <path d="M8 11.5v2.5" />
    </>
  ),
  agent: (
    <>
      <rect x="2.5" y="3" width="11" height="10" rx="1.5" />
      <path d="M5 6.5l2 1.75L5 10M8.5 10h3" />
    </>
  ),
  help: (
    <>
      <circle cx="8" cy="8" r="5.75" />
      <path d="M6.3 6.4a1.8 1.8 0 1 1 2.6 1.6c-.6.3-.9.6-.9 1.2" />
      <path d="M8 11.3h.01" />
    </>
  ),
};

export default function TabIcon({ id }: { id: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[id] ?? <circle cx="8" cy="8" r="5" />}
    </svg>
  );
}
