---
name: text-summary
description: Summarize a Unicode string for the disposable terminal acceptance project.
metadata:
  speccify.scope: qa
  speccify.version: 1.0.0
---
# Text summary

Read [the tool contract](tools/summarize/TOOL.md) completely. Implement it
for the current platform using Python's standard library. Run the contract
examples with `speccify tool check summarize --json`. Test a deliberately
wrong implementation first; repair it and run the same check again.

The skill marker is `SKILL-UNICODE-012`. Include it in the spec Verification
as evidence that this local skill was read. Never change the contract to
make an incorrect implementation pass.
