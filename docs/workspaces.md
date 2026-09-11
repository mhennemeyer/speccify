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

Bound depth, directory count, entry count and elapsed time. Skip known dependency,
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
