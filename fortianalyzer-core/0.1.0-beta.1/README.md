# FortiAnalyzer Core 0.1.0 Beta

SIEM analytics beta for FortiAnalyzer. This package exists so FortiAnalyzer
appears in the marketplace while appliance validation is still pending.

## Authentication

Use a FortiAnalyzer REST API Admin API key with JSON API read access. Configure
trusted hosts so FortiAnalyzer accepts requests from the FortiDashboard API
source IP.

## Current scope

- Marketplace listing and installable package metadata.
- Health probe: `POST /jsonrpc` with `method=get` and `url=/sys/status`.
- Preview widgets for health, ADOM/log posture, event taxonomy and ingestion
  readiness. All widget payloads are marked `applianceValidated=false`.
- Event ingestion: empty list until log/ADOM pagination is validated in a lab.
- Draft-only playbook action for analyst signal review. It is always `dryRun`
  and never changes FortiAnalyzer state.

No configuration writes, live log ingestion, live widgets, or live playbook
actions are included in this beta package.
