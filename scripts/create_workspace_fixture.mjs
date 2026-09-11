// Create an isolated native-review workspace. No network or existing repo changes.
import { mkdtemp, mkdir, writeFile, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

const root = await realpath(await mkdtemp(join(tmpdir(), "speccify-workspace-review-")));
const git = (cwd, args) => execFileSync("git", args, { cwd, stdio: "pipe",
  env: { ...process.env, GIT_CONFIG_NOSYSTEM: "1", GIT_CONFIG_GLOBAL: process.platform === "win32" ? "NUL" : "/dev/null" } });
for (const name of ["api", "web"]) {
  const path = join(root, name);
  await mkdir(join(path, ".agent/specs/001-start"), { recursive: true });
  await mkdir(join(path, ".agent/skills/review"), { recursive: true });
  await writeFile(join(path, ".agent/specs/001-start/SPEC.md"), `---\nstation: Backlog\ncreated: 2026-09-11\n---\n# ${name}: isolated review\n\n## Tasks\n\n- [ ] Review this repository only.\n`);
  await writeFile(join(path, ".agent/skills/review/SKILL.md"), `---\nname: review\ndescription: Review the ${name} project\n---\n# Review ${name}\n\nKeep this project's context separate.\n`);
  await writeFile(join(path, "README.md"), `# ${name}\n\nDisposable workspace review fixture.\n`);
  git(path, ["init", "-b", "main"]);
  git(path, ["add", "."]);
  git(path, ["-c", "user.name=Demo", "-c", "user.email=demo@example.invalid", "commit", "-m", "chore: create review fixture"]);
}
git(join(root, "api"), ["worktree", "add", "-b", "feature/search", join(root, "api-search")]);
console.log(root);
