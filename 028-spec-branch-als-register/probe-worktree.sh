set -u
# Probelauf zu Spec 028: in einem leeren Ordner ausführen (legt origin.git, A, B, C an).
P="$(cd "$(dirname "$0")" && pwd)"; cd "$P"
export GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=A GIT_AUTHOR_EMAIL=a@x GIT_COMMITTER_NAME=A GIT_COMMITTER_EMAIL=a@x
git init -q --bare origin.git
git clone -q origin.git A 2>/dev/null; cd A; git checkout -q -b main
mkdir -p .agent/specs/001-x src; printf -- '---\nstation: Backlog\norder: 1\n---\n# X\n\n## Tasks\n\n- [ ] eins\n- [ ] zwei\n' > .agent/specs/001-x/SPEC.md
printf '{"timestamp":"t0","spec_id":"001-x","event_type":"spec_created","actor":"user","summary":"angelegt"}\n' > .agent/specs/001-x/history.jsonl
echo code > src/main.rs; git add -A; git commit -qm "vor Migration"; git push -q -u origin main
PRE=$(git rev-parse HEAD)
echo "== Migration: orphan branch specs aus .agent/specs"
cp -R .agent/specs "$P/specs-copy"
git switch -q --orphan specs; cp -R "$P/specs-copy"/. . ; printf '*.jsonl merge=union\n' > .gitattributes
git add -A; git commit -qm "specs: Register aus main übernommen"; git push -q -u origin specs
git switch -q main; git rm -rq .agent/specs; printf '.agent/specs/\n' >> .gitignore; git add -A; git commit -qm "chore: .agent/specs wird Worktree des Branch specs"; git push -q origin main
git worktree add -q .agent/specs specs; echo "outer status: [$(git status --short)] inner branch: $(git -C .agent/specs branch --show-current) inhalt: $(ls .agent/specs | tr '\n' ' ')"
echo "== Klon B mit Worktree"
cd "$P"; git clone -q origin.git B 2>/dev/null; cd B; git worktree add -q --track -b specs .agent/specs origin/specs; echo "B sieht: $(ls .agent/specs | tr '\n' ' ') auf $(git -C .agent/specs branch --show-current); outer status [$(git status --short)]; code-branch $(git branch --show-current)"
echo "== A auf Feature-Branch, tickt Task im Worktree, pusht nur specs"
cd "$P/A"; git switch -q -c spec/001-x; sed -i '' 's/- \[ \] eins/- [x] eins/; s/station: Backlog/station: Doing/' .agent/specs/001-x/SPEC.md
printf '{"timestamp":"t1","spec_id":"001-x","event_type":"station_changed","actor":"A","summary":"Doing"}\n' >> .agent/specs/001-x/history.jsonl
git -C .agent/specs commit -qam "spec(001-x): Doing, Task 1"; git -C .agent/specs push -q origin specs; echo "A code-branch: $(git branch --show-current), outer status [$(git status --short)]"
cd "$P/B"; git -C .agent/specs pull -q --rebase; echo "B nach pull: $(grep -c '\[x\]' .agent/specs/001-x/SPEC.md) getickt, $(grep station .agent/specs/001-x/SPEC.md), B code-branch $(git branch --show-current)"
echo "== Gleichzeitig: beide hängen History an, verschiedene Zeilen in SPEC.md"
export GIT_AUTHOR_NAME=B GIT_COMMITTER_NAME=B
sed -i '' 's/- \[ \] zwei/- [x] zwei/' .agent/specs/001-x/SPEC.md; printf '{"timestamp":"t2","spec_id":"001-x","event_type":"agent_run","actor":"B","summary":"Task 2"}\n' >> .agent/specs/001-x/history.jsonl
git -C .agent/specs commit -qam "spec(001-x): Task 2"; git -C .agent/specs push -q origin specs
cd "$P/A"; export GIT_AUTHOR_NAME=A GIT_COMMITTER_NAME=A
sed -i '' 's/^order: 1/order: 2/' .agent/specs/001-x/SPEC.md; printf '{"timestamp":"t3","spec_id":"001-x","event_type":"spec_edited","actor":"A","summary":"order"}\n' >> .agent/specs/001-x/history.jsonl
git -C .agent/specs commit -qam "spec(001-x): order"; if git -C .agent/specs pull -q --rebase; then echo "rebase ok; history-Zeilen: $(wc -l < .agent/specs/001-x/history.jsonl | tr -d ' '), Ticks: $(grep -c '\[x\]' .agent/specs/001-x/SPEC.md), $(grep order .agent/specs/001-x/SPEC.md)"; else echo "REBASE FAILED"; git -C .agent/specs status --short; fi; git -C .agent/specs push -q origin specs
echo "== Konflikt: beide ändern station"
cd "$P/B"; git -C .agent/specs pull -q --rebase; sed -i '' 's/station: Doing/station: Done/' .agent/specs/001-x/SPEC.md; git -C .agent/specs commit -qam "B: Done"; git -C .agent/specs push -q origin specs
cd "$P/A"; sed -i '' 's/station: Doing/station: Backlog/' .agent/specs/001-x/SPEC.md; git -C .agent/specs commit -qam "A: Backlog"; git -C .agent/specs pull --rebase 2>&1 | grep -i "conflict" | head -2; echo "Konfliktdateien: $(git -C .agent/specs diff --name-only --diff-filter=U)"; git -C .agent/specs rebase --abort; echo "abort ok, inner: $(git -C .agent/specs status --short | tr '\n' ' ') outer status [$(git status --short)]"
echo "== Migrationsfalle: alter Branch mit getracktem .agent/specs"
cd "$P/B"; git branch -q old "$PRE"; git switch old 2>&1 | head -3; echo "B branch jetzt: $(git branch --show-current); Worktree noch da: $(ls .agent/specs | tr '\n' ' ')"
echo "== Frischer Klon ohne Worktree: was sieht ein Agent?"; cd "$P"; git clone -q origin.git C 2>/dev/null; ls C/.agent 2>&1 | head -1; echo "== Worktree-Liste A"; cd "$P/A"; git worktree list | sed "s|$P|…|"
