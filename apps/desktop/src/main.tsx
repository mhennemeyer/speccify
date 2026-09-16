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

// Spec 039: lesende Haken für die QA-Brücke (ohne Brücke wirkungslos).
installQaHooks();

// Ein Bundle, zwei Fenstertypen (Plan projektfenster.md, D15): das
// Dashboard ("main") und Projektfenster ("project-<hash>"), erkennbar am
// Fenster-Label — synchron verfügbar, kein Flackern beim Start.
const isProjectWindow = getCurrentWebviewWindow().label.startsWith("project-");

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <UpdateUi notifications={!getCurrentWebviewWindow().label.startsWith("ask-")} />
    {getCurrentWebviewWindow().label.startsWith("ask-") ? <AskWindow /> : getCurrentWebviewWindow().label.startsWith("workspace-") ? <WorkspaceShell /> : isProjectWindow ? <ProjectShell /> : <App />}
  </React.StrictMode>,
);
