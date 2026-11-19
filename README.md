# Policies Page Composer

Read-only foundation for the Birchstone **DB.Policies → searchable Interact policy directory** workflow. This project is independent of Property Details Page Composer.

**Current status:** render and preview only. No Interact publishing, Portal task registration, or scheduling is enabled.

## Supported Notion properties

- `Name` — title
- `Number` — rich text or number (preserved as text, e.g. `1.10 Entrata`)
- `Deep Link` — Grace Hill redirect URL
- `Manual` — select or multi-select
- `Keywords` — multi-select or comma-separated rich text

## Local validation and preview

Python 3.10+; standard library only.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/render_workflow.py --fixture examples/notion_fixture.json --minimum-count 1
```

Open `output/policies.preview.html` to view the generated directory.

## Live Notion data (read-only)

Grant your Notion integration access to DB.Policies. Set `NOTION_TOKEN` and **either** `NOTION_DATA_SOURCE_ID` (new API) **or** `NOTION_DATABASE_ID` (legacy API). Never commit credentials.

```bash
export NOTION_TOKEN='...'
export NOTION_DATA_SOURCE_ID='...'
export POLICIES_MIN_COUNT=371
python3 scripts/render_workflow.py --minimum-count "$POLICIES_MIN_COUNT"
```

Review the actual record count and Notion property types before enabling a live workflow. The minimum count is a safety floor, not an exact target; it must be selected based on the active database. Invalid entries, duplicate links, and duplicate manual/number pairs cause validation to fail before saved output is replaced.

## Artifacts (gitignored)

- `output/policies.preview.html` — standalone preview
- `output/policies.fragment.html` — saved validated HTML reserved for future publishing
- `output/render_manifest.json` — policy count, UTC timestamp, content SHA-256 and source; `publish_authorized=false`

The current HTML contains embedded styles and filter JavaScript for local preview. Before publishing to Interact, generate a compatible fragment and move UI assets into `birchstone-interact-customization/policies/`.

## Next implementation phases

1. Verify the live Notion schema, permissions and full policy count.
2. Create Interact-compatible HTML/CSS/JS assets with an isolated preview.
3. Add guarded publisher with destination allowlist and manifest verification.
4. Register Render, View Render, Publish and Render & Publish in Birchstone Portal.
5. Add render-only scheduling; require separate authorization for unattended publication.

**Do not use the Property Details Interact page (2186) as the destination for this project.**
