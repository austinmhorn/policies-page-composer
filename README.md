# Policies Page Composer

Standalone **DB.Policies → searchable Interact policy directory** project, designed to mirror the Property Details Composer workflow without changing the production Property Data Engine.

**Current stage: Go extraction, Python rendering, and one-time Interact page creation.** The page creation tool requires explicit approval and creates only a new page. Updating/publishing existing pages, Portal task registration, and automation are not enabled.

## Architecture

```text
Notion DB.Policies
    ↓
Go: cmd/policies-fetch
    ├── internal/notionapi/     (stateless pagination + auth)
    └── internal/policies/      (type-aware policy normalization)
    ↓
data/policies.json             (gitignored normalized snapshot)
    ↓
Python: scripts/render_workflow.py
    ├── validate required fields, links, duplicates and minimum count
    ├── output/policies.preview.html
    ├── output/policies.fragment.html
    └── output/render_manifest.json
```

The original PDE `notionapi/notionapi.go` was used as a design reference (pagination and Notion property extraction). This project's client is independent and has **no dependency on PDE's config.json, API response file, token globals, or execution**. No shared Go module or PDE code change has been made yet. Once validated, a separate shared-client refactor can be considered.

## Setup

Go 1.23+ and Python 3.10+ are required. No external Go or Python dependencies.

Give the Notion integration read access to DB.Policies. Set `NOTION_TOKEN` and **exactly one** of `NOTION_DATA_SOURCE_ID` (current Notion API) or `NOTION_DATABASE_ID` (legacy API).

```bash
export NOTION_TOKEN='...'
export NOTION_DATA_SOURCE_ID='...'
unset NOTION_DATABASE_ID
export POLICIES_MIN_COUNT=371 # set to the verified active policy count/safety floor
python3 scripts/render_workflow.py --minimum-count "$POLICIES_MIN_COUNT"
```

The Go fetcher uses Notion API version 2025-09-03 for data sources and 2022-06-28 for legacy database queries. It retrieves all pages with cursor pagination and produces a `data/policies.json` snapshot. The Python layer validates and renders that snapshot. Keep tokens in a protected environment, never in the repository.

Alternatively fetch without rendering:

```bash
go run ./cmd/policies-fetch --output data/policies.json
python3 scripts/render_workflow.py --policies-json data/policies.json --minimum-count 371
```

## Test (offline)

```bash
go test ./...
python3 -m unittest discover -s tests -v
python3 scripts/render_workflow.py --fixture examples/notion_fixture.json --minimum-count 1
```

## DB.Policies schema

| Property | Expected Notion type | Use |
|---|---|---|
| Name | title | Policy name |
| Number | rich_text or number | Identifier preserved as text (e.g. `1.10 Entrata`) |
| Manual | select or multi_select | Directory grouping |
| Deep Link | url | Grace Hill redirect link |
| Keywords | multi_select or rich_text | Optional search terms |

Deep links are validated against `https://performancehq.gracehill.com/auth/policy_deep_link_redirect`, including nonempty `manual_id`, `policy_id`, and the `birchstone` subdomain.

Generated snapshots, previews and credentials are gitignored. Do not commit live Notion data or tokens.

## Create a new pure-HTML Interact page (one-time setup)

The separate `scripts/create_page.py` follows Property Details Composer's `scripts/create_test_page.py` and its Interact `POST /api/page/composer` contract. It creates a published, non-public, pure HTML page containing only an initial **Policy Library** placeholder. It does **not** overwrite existing pages or run the Go extractor.

Obtain the correct **Policies** category and top-section IDs from Interact. Do not assume that Property Details' category/section IDs are appropriate. Run a no-network payload preview:

```bash
python3 scripts/create_page.py --category-ids 123 --top-section-ids 456
```

The numeric IDs in this example are placeholders; replace them with actual approved IDs. The preview does not require API credentials and prints the proposed page payload.

For one-time creation, securely configure `INTERACT_API_DOMAIN`, `INTERACT_TENANT_GUID`, `INTERACT_API_KEY`, `INTERACT_API_SECRET`, and `INTERACT_PERSON_ID`. Then run:

```bash
python3 scripts/create_page.py \
  --category-ids ACTUAL_CATEGORY_ID \
  --top-section-ids ACTUAL_TOP_SECTION_ID \
  --create \
  --confirm-title "Birchstone Policy Library"
```

`--create` initiates **an actual Interact publication**, so review the destination category/section and payload first. It requires an exact title confirmation; it does not silently default to creating a page. The script prints the Interact response to identify the new page ID. Record that ID separately before implementing guarded updates. This page is a placeholder; the full searchable directory requires Interact-specific asset work.

`--html-file` can supply a reviewed plain HTML fragment instead of the placeholder, but is optional and not used in the normal first-page setup.

## Safety and follow-up phases

- Current output is a **standalone local preview** containing embedded CSS/JS. Before Interact publishing, move assets into `birchstone-interact-customization/policies/` and generate an Interact-compatible fragment.
- A **page-update publishing** entrypoint does not exist yet. One-time page creation is provided separately. Any new publisher must require an explicitly allowlisted destination (never Property Details page 2186), validate the saved manifest/content hash and refuse stale or unexpected snapshots.
- Register Portal render/preview/publish actions only after a verified live Notion fetch and Interact staging test.
- Scheduled rendering should be enabled separately from unattended publishing.
- When a shared Go notion client is justified, migrate PDE under its own tests and change-control process; do not modify the existing PDE in this project.
