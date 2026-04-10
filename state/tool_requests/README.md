# Tool Requests

Canonical tool requests live here as one JSON file per request.

Minimum schema:
```json
{
  "id": "hb3-github-pages",
  "heartbeat": 3,
  "tool": "GitHub Pages deployment",
  "why": "Need the approved public deploy lane for G2.",
  "plan": "Publish the static site and verify the public URL.",
  "risk": "LOW",
  "alternatives_considered": [
    "Local preview does not satisfy G2."
  ]
}
```

Rules:
- One request per file.
- File extension must be `.json`.
- `risk` must be `LOW`, `MEDIUM`, or `HIGH`.
- `alternatives_considered` must be a non-empty list of strings.
- Canonical outcomes are recorded in `state/tool_grants.json`.

Processing:
```bash
python tools/process_tool_requests.py
```

The rendered markdown summary is `TOOL_GRANTS.md`, but the canonical record is `state/tool_grants.json`.
