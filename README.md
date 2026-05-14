# fortidashboard-addons

Public registry of add-on manifests consumed by [FortiDashboard](https://github.com/ping-wins) at runtime.

Each subdirectory holds one provider integration described by an `addon.json`
manifest. The dashboard API loads every manifest at boot and exposes them
under `/api/marketplace/addons`. The marketplace tab inside the cockpit lists
them and drives the connect form from `provider.auth.fields`.

## Layout

```
fortidashboard-addons/
  README.md
  <addon-id>/
    addon.json          # required manifest
    icon.svg            # optional, rendered in marketplace card
    docs/...            # optional, vendor docs / release notes
```

## Manifest contract

Authoritative pydantic schema lives in the dashboard repo at
`apps/api/app/addons/manifest.py`. Required fields:

- `id`, `version` — stable identifier and semver of the manifest itself.
- `name`, `vendor`, `category`, `description` — listing metadata.
- `provider.type` — gateway-side connector name (`fortigate`, `palo-alto`, ...).
- `provider.auth.kind` + `provider.auth.fields` — schema for the connect form.
- `routes` — every REST path the connector calls (used for docs and audit).
- `widgets` — widget catalog ids the add-on contributes.
- `siemEventTypes` — event type strings the connector emits.

Optional fields:

- `compatibility.minProviderVersion` — minimum vendor firmware/version the
  manifest was validated against. Routes that only exist on newer firmware
  may also carry their own `minProviderVersion`.
- `compatibility.testedVersions` — explicit list of vendor versions the
  manifest has been verified on.
- `compatibility.notes` — free text describing version-specific quirks
  (path differences, envelope shape, required filter syntax, ...).

## Adding a new add-on

1. Create `<addon-id>/addon.json`. Validate it locally against the dashboard
   schema by running, from a FortiDashboard checkout:
   ```bash
   uv run python -c "from app.addons.registry import list_addons; print(list_addons())"
   ```
2. Open a pull request. CI in the dashboard repo will pull the registry on
   release builds and fail if the manifest is invalid.
3. After merge, cut a tag (`v<n>.<n>.<n>`). The dashboard pins the registry
   to a tag, not `main`.

## Current add-ons

| ID              | Vendor    | Category | Min provider version |
|-----------------|-----------|----------|----------------------|
| fortigate-core  | Fortinet  | firewall | FortiOS 7.6.0        |

## Versioning

The registry itself is versioned with git tags. Each `addon.json` carries its
own semver in `version`; bump it whenever the route set, auth schema, widget
catalog or SIEM event types change in a way that affects consumers.
