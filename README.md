# FortiDashboard Add-ons

Marketplace add-on packages installed by FortiDashboard at runtime.

## Layout

    <addon-id>/<version>/addon.json          # AddonManifest (pydantic-validated)
    <addon-id>/<version>/connector/__init__.py  # must expose get_connector(config) -> connector

`connector` is the manifest `entrypoint` (default). The connector object must
implement: `health_check() -> dict`, `get_widget_data(req) -> dict`,
`ingest_events(since) -> list`, `close() -> None`. Optional duck-typed:
`list_playbook_actions() -> list[dict]`, `run_playbook_action(action_id, params) -> dict`.

Packages are self-contained: stdlib + httpx only, no imports from the dashboard.

## Releasing

Tag a version so the dashboard install flow can fetch it:

    git tag <addon-id>-v<version> && git push origin <addon-id>-v<version>

The dashboard fetches `https://api.github.com/repos/ping-wins/fortidashboard-addons/tarball/<tag>`
and expects the package at `<addon-id>/<version>/` inside the tarball.
