import { playbookStatus } from "../src/lib/playbooks.ts";

export function installPlaybookFixture(responses) {
  const control = window.__SPECCIFY_MOCK__;
  const key = "speccify.test.playbookFiles";
  const files = control.playbookFiles = JSON.parse(localStorage.getItem(key) ?? "null") ?? {
    ".agent/playbooks/legacy.md": "# Legacy procedure\n\nExisting procedure.\n",
    ".agent/playbooks/research.md": "---\r\nstatus: draft\r\ncustom: keep-me\r\ndescription: Server research\r\n---\r\n# Research\r\n\r\nIdeas, not instructions.\r\n",
    ".agent/playbooks/unknown.md": "---\nstatus: published\n---\n# Unknown status\n",
  };
  control.playbookCalls = [];
  const save = () => localStorage.setItem(key, JSON.stringify(files));
  const originalRead = responses.project_read_file;
  responses.project_playbooks = () => Object.entries(files).map(([file, text]) => ({
    file, title: /^# (.+)$/m.exec(text.replaceAll("\r", ""))?.[1] ?? file,
    description: /^description: (.+)$/m.exec(text.replaceAll("\r", ""))?.[1] ?? null,
    status: playbookStatus(text),
  }));
  responses.project_read_file = async args => {
    if (!(args.file in files)) return originalRead(args);
    const text = files[args.file];
    if (control.playbookReadDelay) await new Promise(resolve => setTimeout(resolve, control.playbookReadDelay));
    return text;
  };
  responses.project_write_file = args => {
    control.playbookCalls.push(args);
    if (args.expectedContent !== undefined && files[args.file] !== args.expectedContent) throw Error("Datei wurde zwischenzeitlich geändert. Entwurf bleibt erhalten.");
    files[args.file] = args.content;
    save();
  };
  responses.project_playbook_create = ({ name, status }) => {
    const file = `.agent/playbooks/${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.md`;
    if (file in files) throw Error("Exists");
    files[file] = `---\nstatus: ${status ?? "active"}\n---\n# ${name}\n`;
    save();
    return file;
  };
  responses.project_playbook_delete = ({ file }) => { delete files[file]; save(); };
  responses["plugin:clipboard-manager|write_text"] = ({ text }) => { control.copiedPlaybook = text; };
}
