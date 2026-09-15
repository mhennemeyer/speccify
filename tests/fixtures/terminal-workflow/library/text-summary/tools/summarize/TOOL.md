---
name: summarize
description: Return uppercase text and its Unicode code point count.
inputs:
  type: object
  required: [text]
  properties:
    text: {type: string}
outputs:
  type: object
  required: [ok, upper, length]
  properties:
    ok: {const: true}
    upper: {type: string}
    length: {type: integer, minimum: 0}
effects: none
runtime: python
platforms: [macos, linux, windows]
---
# Summarize

Read one JSON object from stdin. Write one JSON object to stdout and exit 0.
`upper` uses Python's Unicode uppercase rules. `length` counts code points
in the original string, not bytes or grapheme clusters. No files, network,
credentials or external commands. Python's standard library is sufficient.

## Examples

### ASCII
input: {"text": "hello"}
output: {"ok": true, "upper": "HELLO", "length": 5}

### Unicode expansion and emoji
input: {"text": "Straße 🌍"}
output: {"ok": true, "upper": "STRASSE 🌍", "length": 8}

### Empty
input: {"text": ""}
output: {"ok": true, "upper": "", "length": 0}

### Multiline
input: {"text": "a\nb"}
output: {"ok": true, "upper": "A\nB", "length": 3}
