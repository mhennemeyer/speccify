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
running terminal, Git operation, action or editor. Aggregated board and project
badges are a follow-up, not an implicit merge of `.agent` trees.

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
