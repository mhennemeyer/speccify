import React from "react";
import ReactDOM from "react-dom/client";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import App from "./App";
import ProjectShell from "./ProjectShell";
import WorkspaceShell from "./WorkspaceShell";
import AskWindow from "./AskWindow";
import "./index.css";
import { installQaHooks } from "./lib/qa";
import UpdateUi from "./components/UpdateUi";
import { initLanguage, useLanguage } from "./i18n";

// Spec 039: lesende Haken für die QA-Brücke (ohne Brücke wirkungslos).
installQaHooks();
// Spec 073: Oberflächensprache aus den Einstellungen, Wechsel anderer Fenster hören.
initLanguage();

// Ein Bundle, zwei Fenstertypen (Plan projektfenster.md, D15): das
// Dashboard ("main") und Projektfenster ("project-<hash>"), erkennbar am
// Fenster-Label — synchron verfügbar, kein Flackern beim Start.
const label = getCurrentWebviewWindow().label;
const isProjectWindow = label.startsWith("project-");

function windowContent() {
  if (label.startsWith("ask-")) return <AskWindow />;
  if (label.startsWith("workspace-")) return <WorkspaceShell />;
  return isProjectWindow ? <ProjectShell /> : <App />;
}

/** Rendert den Fensterinhalt bei jedem Sprachwechsel neu — die Elemente
 *  entstehen hier, deshalb rendert der ganze Baum mit (Spec 073). Kein
 *  `key`-Wechsel: Zustand (Entwürfe, Tabs, Terminals) bleibt erhalten. */
function Root() {
  useLanguage();
  return (
    <>
      <UpdateUi notifications={!label.startsWith("ask-")} />
      {windowContent()}
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
