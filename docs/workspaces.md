# Workspace contract v1

Spec: 015-workspace-projekterkennung. Native implementation: `workspace_cmd.rs`.

## Ownership and identity

A workspace is a selected local directory. A project is a named logical group.
A repository is one canonical Git common directory; multiple worktrees share it.
A plain folder project has no Git common directory. IDs are opaque UUIDs generated
once and stored, not derived from display names or remote URLs. Two clones with
the same remote remain separate repositories: no network-based identity guesses.

`~/.speccify/workspaces.json` stores format version, workspaces and revisions.
Each workspace stores projects (IDs/names/membership), repositories (IDs and default
project ID), and worktree bindings (IDs/local paths/relative paths/observed markers).
Grouping and renaming only change metadata in this local store. This file is not
a team register or a tracked project manifest; shared identity binding is Spec 016.
Existing recent-project/open-window files and repository contents are untouched.
Spec 026 adds an optional `window_open` preference (default false for existing
stores) to each workspace. It is independent of mapping revisions. Workspace
windows are restored at app launch and forgotten on explicit window close.

Every repository starts in its own project. Grouping creates a logical project;
ungrouping restores the repository's original project ID. Empty project identities
are retained for this purpose. Display-name changes never change IDs. A filesystem
move is not inferred from a matching name: explicit relocation is future work.

## Discovery

Scan the selected canonical directory, including nested repositories. Recognize
`.git` directories, `.git` pointer files and worktree `commondir` metadata without
executing Git, hooks, project scripts or network commands. Only small metadata
files are read outside the selected root when a Git pointer requires it; do not
enumerate or open external worktrees. Symlinks are skipped. Canonical common-dir
identity deduplicates worktrees, not arbitrary clones sharing a remote.

Bound depth (16 levels below the selected root), directory count (2,000), entry
count (20,000) and elapsed time (three seconds best-effort between directories,
not a hard filesystem I/O timeout). A leaf at the depth limit is fully scanned;
only skipped child directories make the result partial. Depth diagnostics list
up to eight sorted relative paths plus the remaining count, even if another
budget also stops the scan. Entry/time/directory limits identify the current
directory, not an exhaustive list of unread paths. Available projects remain
usable. A complete rescan clears previous warnings without changing identities,
names or groups (Spec 025). Skip known dependency,
build and metadata directories; report scan limits, invalid Git pointers and read
errors. A partial scan never removes old bindings. Missing bindings remain visible
as unavailable; opening a worktree revalidates the path. No automatic Git init or
workflow setup. Plain roots and nested folders with Speccify markers stay usable.

## Persistence and concurrency

The native adapter serializes read/modify/write operations, checks the caller's
expected workspace revision and atomically replaces the store via a same-directory
temporary file. Missing store means empty; malformed/unsupported stores produce
an error and are not overwritten. Limits protect reads of malformed giant files.
The frontend reloads after conflicts; it must not silently retry a stale edit.
Discovery runs off the UI thread. Rescans merge by worktree path/common directory,
preserve IDs, names and grouping, and report partial results explicitly.

## UI and execution boundary

Dashboard: choose folder → inspect workspace → select repos → group/name/ungroup →
open an explicitly named worktree. Every opened worktree uses existing project
window identity and its own terminal cwd. Workspace selection never retargets a
running terminal, Git operation, action or editor. Spec 024 adds a read-only
aggregated board; it does not merge `.agent` trees or grant cross-project writes.

## Shared work window (Spec 026)

Dashboard → **Workspace öffnen** opens/focuses one `workspace-<id>` window. Its
binding comes from the native window label and local workspace store, never from
an arbitrary URL path. Existing single-project windows are unaffected. Missing
workspace data fails explicitly; missing individual worktrees remain visible.
`workspace_resolve_target` revalidates each worktree path/common-directory binding
before its pane is mounted and on explicit workspace refresh. This is not a new
filesystem security sandbox: existing native per-project mutation checks still apply.

The workspace shell groups navigation by logical project, repository and worktree.
Its common board lists specs in those groups and retains independent card keys.
Selection shows the original project's existing spec inspector, task toggles,
questions/history and editor. New-spec buttons name the destination repository.
There is no aggregate write command or cross-repository drag-and-drop; changes use
the existing per-project APIs and trigger a fresh shared snapshot. The dashboard
preview remains read-only. Snapshot refresh never changes the active project.

Files, Git, playbooks, skills, tools, actions, MCP configuration and agent settings
reuse existing project components with immutable worktree paths. Editors and
commit drafts stay mounted while hidden; regrouping moves navigation portals, not
the components holding processes and drafts. Spec editor dialogs are local to their
selected worktree; external updates are subject to existing editor concurrency rules.
Changing an actual path binding requires reopening; no live process is retargeted.

Workspace terminals start only on an explicit click; empty command means a shell.
Switching projects or sections preserves each started terminal and action output.
There is no automatic multi-agent start or promise of terminal resumption after app
quit. Every terminal instance has a UUID, including development lifecycle probes.
Window-wide Git, action, file-open and type-command listeners are gated by active
project context. Output/exit events remain matched to their unique execution IDs.
Typing a command without a started terminal still requires starting that project's
terminal and retrying; no invisible command queue or automatic execution is implied.

Watchers are keyed by window, canonical worktree path and lease ID. A stale cleanup
cannot stop a newer watcher or another root's watcher. `project-changed` includes
the project path; workspace listeners route it to that pane and refresh the shared
board for board changes. Mapping refresh is explicit. Existing project windows can
still stop all their own watchers with the old no-argument stop call.

## Read-only board snapshot (Spec 024)

`workspace_board(workspace_id)` returns the workspace revision, capture timestamp,
entries and explicit partial-result warnings. Each entry contains the existing
project-board spec representation plus project/repository/worktree IDs and labels.
Both boards use `project_cmd::spec_from_text`; no competing frontmatter/task parser.
The key is an encoded tuple of workspace ID, repository ID, worktree ID and relative
spec path. Renaming/grouping cannot change it. Identical spec IDs across repos,
worktrees or historical paths remain distinct; this is not a shared team spec ID.

Revalidate every worktree before reading. Do not follow linked `.agent`, `specs`,
historical directories, spec directories or files. Missing knowledge directories
mean no specs; inaccessible/invalid sources produce warnings. Existing historical
specs remain labelled read-only entries, without an archive action. Unknown stations
remain visible with their original names. The parser matches single-project behavior.

Bounds per request: 100 worktrees, 5,000 directory entries, 256 KiB per document,
8 MiB aggregate text budget (the final document can exceed the threshold by up to
256 KiB), three seconds best-effort between filesystem operations. OS filesystem
calls can still block; these limits are not a hard I/O timeout or an adversarial
filesystem race-proof sandbox. The snapshot is not transactional across files.
Unread sources are reported, never replaced with a misleading empty success.

The dashboard offers project filter, search, matching list/cards and a read-only
preview. Refresh is explicit; file watchers/team sync are not implied. Failed refresh
labels the previous same-workspace snapshot as potentially stale. Workspace changes
reset the component and ignore late responses. Opening revalidates the worktree via
the existing `workspace_open` command; it opens that project's window, not a spec
deep link. Editing/acceptance stays in that window. There is no aggregate write API.

## Fixture matrix

Two independent repos; nested repo; linked worktree inside/outside scan root;
submodule-style `.git` pointer; same-remote clones; plain root; Speccify-marked
non-Git child; ignored dependency dirs; symlink loop; malformed/oversized pointer;
depth/entry budget; corrupt store; revision conflict; rename/group/rescan/reload/
ungroup with stable IDs; unavailable path. Compare repo/index bytes before/after.

For native review, run `node scripts/create_workspace_fixture.mjs`. It prints a
new temporary workspace containing `api`, `web` and the linked `api-search`
worktree. Both repos intentionally contain a spec numbered `001` and a skill
named `review`; their contents must stay separate. In Dashboard → Projekte,
discover the printed root, group the two repos, restart, rescan and ungroup.
Open `api-search` explicitly and verify the feature worktree's own project window.
The script does not touch existing repos or use the network. Keep the temporary
fixture while reviewing; it is not a permanent workspace or shared team register.

For a read-only discovery smoke test against an explicitly selected real folder:
`SPECCIFY_DISCOVERY_SMOKE_ROOT=/absolute/workspace cargo test -p speccify-desktop
discovery_local_workspace_smoke -- --ignored --nocapture`. It uses production
limits, reports discovered roots and requires a complete warning-free result.
It does not persist the workspace or replace native UI/rescan acceptance.
