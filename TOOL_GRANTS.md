# TOOL GRANTS

Rendered from `state/tool_grants.json`. Canonical tool-request and grant state lives under `state/`.

**No raw secrets here.** Reference secret names only.

## Granted
### GitHub Pages deployment (bootstrap_github_pages_deploy)
**Status**: granted
**Heartbeat**: 0
**Risk**: LOW
**Reason**: Official public product deployment lane for the current pilot class.
**Access**: Use the configured GitHub Pages environment variables and repository settings from state/deployment.json.
**Limits**: GitHub Pages only. No alternate product deploy lane is approved.

### GitHub public repo creation (bootstrap_github_repo_creation)
**Status**: granted
**Heartbeat**: 0
**Risk**: LOW
**Reason**: Public repository creation is pre-granted for the current pilot class.
**Access**: Use the approved GitHub token or secret name documented by the operator.
**Limits**: Public repositories only. Keep credentials out of markdown and canonical state.

## Auto-Approved
_(none)_

## Pending Review
_(none)_

## Denied
_(none)_

## Invalid
_(none)_
