# Terminal workflow acceptance

Spec 012 tests a complete workflow in a disposable project: project rules,
a local skill, a harmless Unicode tool, deliberate failure, repair, CLI/MCP
verification and a spec awaiting human acceptance. Platform and host results
must be recorded separately. A shell or browser mock does not prove that an
authenticated coding host can complete the task.

## Repeatable checks

The normal Python CI job collects `tests/test_terminal_workflow.py`:

```sh
uv run pytest tests/test_terminal_workflow.py
```

It uses real CLI subprocesses and an initialized MCP stdio connection.
It covers setup and skill links, missing → failing → verified tools,
Unicode input, CLI/MCP report parity, read-only verification and rejection
of existing fixture directories. Missing libraries or lockfiles must never
make missing tools appear verified.

The optional native suite reuses the adapter and page objects from the
`speccify-qa` checkout. Start the bundled app with its QA bridge first:

```sh
./scripts/dev.sh --open --ui-port=18768 --qa-bridge=18769
SPECCIFY_QA_ROOT=../speccify-qa uv run pytest scripts/test_terminal_workflow_app.py -s
```

The bridge flag takes effect at process start. Follow the restart procedure
in the development playbook if the app is already running without it.
Missing QA checkout or bridge produces a skip, not a successful acceptance.
The suite creates two temporary projects, opens their windows, uses pure
shell terminals, and closes those windows afterwards. It checks:

- Native workflow setup preserves custom project rules.
- External spec edits update the board without refresh (10-second deadline;
  the watcher polls every two seconds; measured latency is printed).
- Questions survive closing/reopening; fixture answers remain in Decisions.
- Complete fixture work remains Doing and ready, awaiting acceptance.
- Two real PTYs keep output separate; Unicode, Ctrl-C and process exit work.

## Fresh host run

Use a new path for every run, with the prepared workspace interpreter:

```sh
./scripts/fix-venv-hidden.sh
.venv/bin/python scripts/create_terminal_fixture.py /tmp/speccify-terminal-trial
```

On macOS, the installed uv version can hide `.pth` files again on every
`uv run`; execute the repaired `.venv` interpreter directly for this step.
The fixture includes its skill source library, expanded skill/tool contract,
host instruction files, one spec and `.agent/runtime.md` with this machine's
CLI/MCP interpreter, arguments and environment. No implementation is supplied.
It refuses an existing target directory. The source fixture contains no
personal paths; the runtime note binds each local run to its prepared engine.

Open the new project in Speccify, run **Einrichten**, select the host preset
and start a fresh session. Resolve that host's trust/login screen before
using the spec's **Auftrag…** dialog. Insert its implementation request, then
submit it in the terminal. An open PTY alone does not prove host readiness.
Check the resulting files and board, including both rule/skill markers,
the failed check, four passing examples, actual MCP comparison and
`Doing / ready: true / needs_human: true`.

Use a clearly labelled test question to exercise persistence. Leave it open,
restart the app after saving work, verify the saved question and session
choice, then supply a fixture answer. Check that the answer becomes a
decision without an unnecessary repeated question. This test answer does
not constitute human acceptance of the product.

For restart testing, record existing window labels, save drafts and wait for
running work. Quit normally, reopen the same bundle and verify restored
windows, saved spec data and the explicit session choice. A host without a
recorded session ID must show that limitation; do not silently choose its
latest conversation. Leave the main app open afterwards.

Record OS, architecture, bundle version/build, host version, date, commands,
observations and limitations in the spec. A prepared developer Mac does not
prove onboarding on a second Mac or native Windows support.
