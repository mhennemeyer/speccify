import TabIcon from "./TabIcon";
import { isMac } from "../lib/platform";

export const PROJECT_TABS = [
  { id: "board", label: "Specs" }, { id: "files", label: "Dateien" },
  { id: "git", label: "Git" }, { id: "playbooks", label: "Playbooks" },
  { id: "skills", label: "Skills" }, { id: "tools", label: "Tools" },
  { id: "actions", label: "Aktionen" }, { id: "mcps", label: "MCPs" },
  { id: "agent", label: "Agent" }, { id: "help", label: "Hilfe" },
] as const;
export type ProjectTab = typeof PROJECT_TABS[number]["id"];
export const PROJECT_GROUPS: ReadonlyArray<{ id: string; label: string; tone: string; tabs: readonly ProjectTab[] }> = [
  { id: "dateien", label: "Dateien", tone: "blue", tabs: ["files", "git"] },
  { id: "orga", label: "Orga", tone: "violet", tabs: ["playbooks", "skills"] },
  { id: "technik", label: "Technik", tone: "teal", tabs: ["tools", "actions", "mcps", "agent"] },
  { id: "board", label: "Specs", tone: "violet", tabs: ["board"] },
  { id: "help", label: "Hilfe", tone: "slate", tabs: ["help"] },
];
export function projectGroupOf(tab: ProjectTab) {
  return PROJECT_GROUPS.find(group => group.tabs.includes(tab)) ?? PROJECT_GROUPS[0];
}

/** The same two-level navigation in single-project and workspace windows. */
export default function ProjectNavigation({ active, lastTab, activate }: {
  active: ProjectTab; lastTab: Record<string, ProjectTab>; activate: (tab: ProjectTab) => void;
}) {
  const activeGroup = projectGroupOf(active);
  return <>
    <div className="px-2 py-1.5">
      <div role="tablist" aria-label="Bereiche" className="flex gap-0.5 rounded-full bg-slate-100 p-0.5">
        {PROJECT_GROUPS.map((group, index) => <button key={group.id} role="tab"
          aria-selected={activeGroup.id === group.id} data-tone={group.tone} aria-label={group.label}
          title={`${group.label} (${isMac ? "⌘" : "Strg+"}${index + 1})`}
          onClick={() => activate(lastTab[group.id] ?? group.tabs[0])}
          className="accent-tab flex min-h-7 flex-1 items-center justify-center rounded-full">
          <TabIcon id={group.id} />
        </button>)}
      </div>
    </div>
    {activeGroup.tabs.length > 1 ? <div role="tablist" aria-label={activeGroup.label} className="flex gap-1 px-2 pb-1">
      {activeGroup.tabs.map(id => <button key={id} role="tab" aria-selected={active === id}
        data-tone={activeGroup.tone} onClick={() => activate(id)}
        className="accent-tab rounded px-2 py-1 text-xs font-medium">
        {PROJECT_TABS.find(tab => tab.id === id)?.label}
      </button>)}
    </div> : <h2 className="px-3 pb-1 text-xs font-semibold text-slate-500">
      {PROJECT_TABS.find(tab => tab.id === active)?.label}
    </h2>}
  </>;
}
