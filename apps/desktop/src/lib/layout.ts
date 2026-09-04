// Fenster-Layout des Projektfensters (Plan projektfenster.md, W7 —
// Xcode-/iKanban-Muster): Navigator links, Inhalt, Inspektor rechts mit
// Tabs, Terminal wahlweise als rechter Tab oder als Bottom-Bar. Breiten
// und Sichtbarkeiten sind UI-Präferenzen und leben pro Projekt in
// localStorage — sie gehören nicht ins Repository.

export type TerminalDock = "right" | "bottom";
export type RightTab = "inspector" | "terminal";

export interface ProjectLayout {
  navWidth: number;
  navShown: boolean;
  rightWidth: number;
  rightShown: boolean;
  rightTab: RightTab;
  bottomHeight: number;
  bottomShown: boolean;
  terminalDock: TerminalDock;
}

export const LAYOUT_LIMITS = {
  nav: [200, 420] as const,
  right: [280, 900] as const,
  bottom: [140, 800] as const,
};

// Default: Terminal unten (BO 2026-09-04) — so bleibt der Inspektor rechts
// frei für die Auswahl und muss nicht mit dem Terminal um den Tab streiten.
export const DEFAULT_LAYOUT: ProjectLayout = {
  navWidth: 260,
  navShown: true,
  rightWidth: 400,
  rightShown: true,
  rightTab: "inspector",
  bottomHeight: 320,
  bottomShown: true,
  terminalDock: "bottom",
};

/** Griffbreite der Splitter in px (Trefferfläche; sichtbar ist 1 px). */
export const HANDLE_SIZE = 5;

export function clamp(value: number, [min, max]: readonly [number, number]): number {
  return Math.min(max, Math.max(min, value));
}

function layoutKey(project: string) {
  return `speccify.project.layout:${project}`;
}

/** Vor-W7-Schlüssel („rechts ODER unten", BO-Finding 2026-08-28) — wird
 *  einmalig übernommen, damit die bisherige Wahl nicht verloren geht. */
function legacyPositionKey(project: string) {
  return `speccify.project.terminalPosition:${project}`;
}

export function loadLayout(project: string): ProjectLayout {
  const layout: ProjectLayout = { ...DEFAULT_LAYOUT };
  try {
    const stored = localStorage.getItem(layoutKey(project));
    if (stored) {
      const parsed = JSON.parse(stored) as Partial<ProjectLayout>;
      Object.assign(layout, parsed);
    } else if (localStorage.getItem(legacyPositionKey(project)) === "right") {
      layout.terminalDock = "right";
      layout.rightTab = "terminal";
    }
  } catch {
    // localStorage nicht verfügbar oder kaputt — Default bleibt.
  }
  layout.navWidth = clamp(layout.navWidth, LAYOUT_LIMITS.nav);
  layout.rightWidth = clamp(layout.rightWidth, LAYOUT_LIMITS.right);
  layout.bottomHeight = clamp(layout.bottomHeight, LAYOUT_LIMITS.bottom);
  if (layout.terminalDock === "bottom" && layout.rightTab === "terminal") {
    layout.rightTab = "inspector";
  }
  return layout;
}

export function saveLayout(project: string, layout: ProjectLayout): void {
  try {
    localStorage.setItem(layoutKey(project), JSON.stringify(layout));
  } catch {
    // dito
  }
}
