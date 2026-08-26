import React from "react";
import ReactDOM from "react-dom/client";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import App from "./App";
import ProjectShell from "./ProjectShell";
import "./index.css";

// Ein Bundle, zwei Fenstertypen (Plan projektfenster.md, D15): das
// Dashboard ("main") und Projektfenster ("project-<hash>"), erkennbar am
// Fenster-Label — synchron verfügbar, kein Flackern beim Start.
const isProjectWindow = getCurrentWebviewWindow().label.startsWith("project-");

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {isProjectWindow ? <ProjectShell /> : <App />}
  </React.StrictMode>,
);
