import { createContext, useContext, useRef } from "react";

// Single-project windows are active by default. Workspace panes keep their
// state mounted, but only the selected project receives window-wide commands.
export const ProjectActivity = createContext(true);
export function useProjectActivity() {
  const active = useContext(ProjectActivity);
  const current = useRef(active);
  current.current = active;
  return current;
}
