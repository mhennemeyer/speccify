import { createRoot } from "react-dom/client";
import { parse, stringify } from "smol-toml";
import AgentsView from "../src/views/AgentsView";
import "../src/index.css";

const test = {
  files: {
    "codex-config": '# keep\napproval_policy = "on-request"\ncustom_key = "keep"\n[mcp_servers.demo]\ncommand = "demo"\n',
    "claude-settings": '{"permissions":{"defaultMode":"default","allow":["Bash(npm test)"]},"unknown":{"keep":7},"hooks":{}}',
    "codex-agents-md": "Global instructions", "claude-md": "Global instructions",
  } as Record<string, string>,
  writes: [] as string[],
};
// The browser fixture tests interaction; Rust tests cover native validation and persistence.
const internals = (window as any).__TAURI_INTERNALS__;
const original = internals.invoke;
(window as any).__AGENT_SETTINGS_TEST__ = test;
const decode = (id: string, content: string) => id === "codex-config" ? parse(content) : JSON.parse(content || "{}");
internals.invoke = async (command: string, args: any) => {
  if (command === "agent_config_list") return Object.keys(test.files).map(id => ({ id, host: id.startsWith("codex") ? "codex" : "claude", path: `/test/${id}`, hint: "Test", exists: true }));
  if (command === "agent_config_read") return test.files[args.id];
  if (command === "agent_config_parse") return decode(args.id, args.content);
  if (command === "agent_config_patch") {
    const value = decode(args.id, args.content);
    for (const change of args.changes) {
      let parent = value;
      for (const key of change.path.slice(0, -1)) parent = parent[key] ??= {};
      const key = change.path.at(-1);
      if (change.value === null) delete parent[key]; else parent[key] = change.value;
    }
    return args.id === "codex-config" ? stringify(value) : JSON.stringify(value, null, 2);
  }
  if (command === "agent_config_write") {
    if (test.files[args.id] !== args.expectedContent) throw Error("Die Datei wurde außerhalb dieses Editors geändert.");
    if (!args.id.endsWith("md")) decode(args.id, args.content);
    test.files[args.id] = args.content; test.writes.push(args.id); return null;
  }
  return original(command, args);
};
createRoot(document.getElementById("root")!).render(<div className="h-screen bg-white p-5 text-slate-800"><AgentsView /></div>);
