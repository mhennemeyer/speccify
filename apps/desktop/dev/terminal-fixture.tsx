import { createRoot } from "react-dom/client";
import { useState, useEffect } from "react";
import TerminalPanel from "../src/components/TerminalPanel";
import TerminalPreferencesEditor from "../src/components/TerminalPreferencesEditor";
import ThemePicker from "../src/components/ThemePicker";
import { useTheme } from "../src/lib/theme";
import { installQaHooks } from "../src/lib/qa";
import "../src/index.css";
installQaHooks();
function Fixture() {
  const [theme, setTheme] = useTheme();
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const show = () => setVisible(true);
    window.addEventListener("speccify:show-terminal", show);
    return () => window.removeEventListener("speccify:show-terminal", show);
  }, []);
  return <div className="flex h-screen flex-col bg-white text-slate-800">
    <ThemePicker value={theme} onChange={setTheme} />
    <TerminalPreferencesEditor />
    <button onClick={() => setVisible(value => !value)}>Terminal umschalten</button>
    <div className={`terminal-surface min-h-0 flex-1 ${visible ? "flex" : "hidden"}`} data-testid="terminal-pane">
      <TerminalPanel visible={visible} cwd="/test/project" autostart="" />
    </div>
  </div>;
}
createRoot(document.getElementById("root")!).render(<Fixture />);
