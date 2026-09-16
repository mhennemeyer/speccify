# Agent settings schemas

Snapshot: 2026-09-16. Used as a field and help catalogue, not a claim that every
installed CLI supports every option. Unknown keys remain available in the source editor.

- Codex: https://learn.chatgpt.com/docs/config-schema.json
  ([reference](https://learn.chatgpt.com/docs/config-file/config-reference)).
  OpenAI Codex publishes its configuration schema under Apache-2.0.
- Claude Code: https://json.schemastore.org/claude-code-settings.json,
  linked by the [official settings documentation](https://code.claude.com/docs/en/settings).
  SchemaStore schemas are published under the Apache-2.0 license.

The license text is included in `LICENSE-APACHE-2.0`. The schema snapshots are
unmodified JSON data apart from formatting. Copyright remains with their
respective authors.

Update by replacing each complete JSON snapshot from the corresponding URL,
then run the agent configuration tests. Do not fetch schemas when opening settings:
the catalogue must work offline and retain a reviewable version.
