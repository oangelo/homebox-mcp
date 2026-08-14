# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2026-08-15

### Fixed

- The addon dashboard's "🛠️ Available Tools" grid still listed only 8 of
  the 18 tools (a static HTML snippet in `server.py`, missed when the
  `homebox://info` MCP resource and the READMEs' tool tables were brought
  up to date). Now lists all 18.

## [0.5.0] - 2026-08-14

### Added

- **Compatibility with Homebox v0.26.0+ ("entity merge" API change).** In
  v0.26.0 Homebox removed `/items`, `/locations` and `/labels` in favor of a
  unified `/entities` API (+ `/entity-types`, `/tags`). The client now
  **auto-detects** which API the server speaks on first use and
  routes/normalizes calls accordingly, so the addon works unmodified on both
  older and newer Homebox versions with no reconfiguration. See the
  [entity merge migration guide](https://homebox.software/en/advanced/entity-merge-upgrade/).

### Fixed

- **MCP server crashed on every tool call** (`RuntimeError: Task group is not
  initialized`). The FastMCP app is now mounted with its `lifespan` passed to
  the parent Starlette app, required by modern FastMCP to start its session
  manager.
- **Intermittent `AssertionError: Unexpected message: ... 'http.response.start'
  ...`** crashing requests. `BearerAuthMiddleware` was built on
  `starlette.middleware.base.BaseHTTPMiddleware`, which buffers/re-wraps the
  downstream response — incompatible with FastMCP's streaming responses once
  a session has overlapping in-flight requests. Rewritten as raw ASGI
  middleware. See [fastmcp#858](https://github.com/jlowin/fastmcp/issues/858)
  and [python-sdk#883](https://github.com/modelcontextprotocol/python-sdk/issues/883).
- **`Received request before initialization was complete`, failing every
  tool call.** The legacy SSE transport splits a session across two
  independent requests (a `GET /sse` stream handing out a `session_id`, plus
  separate `POST /messages?session_id=...` calls) without checking the GET
  side finished its handshake before accepting POSTs on that session; a
  client reopening a second `/sse` connection (observed from `mcp-remote`)
  could race and land on an uninitialized session. Switched to the modern
  **Streamable HTTP** transport (still mounted at `/sse` for compatibility),
  which tracks sessions via an `Mcp-Session-Id` header instead of two
  endpoints racing over a query param. See
  [python-sdk#423](https://github.com/modelcontextprotocol/python-sdk/issues/423)
  and [python-sdk#1844](https://github.com/modelcontextprotocol/python-sdk/issues/1844).
- **`homebox_list_locations` / `homebox_get_location_tree` returned an empty
  list even when locations existed** (entities mode). Per Homebox's own
  server source, the plain `GET /entities` list excludes locations from its
  results unless `isLocation=true` is passed explicitly (an undocumented
  filter, missing from the swagger annotations) — "for backward
  compatibility" with the old items-only `/items` endpoint. Fixed by
  requesting `GET /entities?isLocation=true` directly, which is also what
  makes the server populate each result's `itemCount`.
- **`homebox_update_label` failed with `422 Unprocessable Entity`** (entities
  mode). Homebox's tag-update endpoint (`repo.TagUpdate`) requires a full
  replacement object where `name` is mandatory even when it isn't changing;
  the client only sent the fields the caller explicitly passed. Now fetches
  the current label first and merges in the requested changes, mirroring the
  pattern already used for items/locations (also preserves `parentId` for
  nested tags, matching the fix already applied to `update_location` in
  0.2.1).
- **`homebox_get_location_tree` made a redundant HTTP request per location.**
  It already got each location's direct parent for free from
  `get_locations()` (eager-loaded by the server), but was still calling
  `get_location()` again for every node to re-fetch the same information.
  Tree-building logic moved into `HomeboxClient.get_location_tree()`, which
  uses that parent directly in entities mode and only falls back to per-node
  fetches for legacy Homebox (whose old `/locations` list genuinely omits
  parent info).
- **`homebox_get_location`'s docstring promised a field that doesn't exist**
  (`items`); the actual field is `children` (a mix of sub-locations and/or
  items), plus `itemCount`.
- **`homebox_list_locations`'s docstring blamed "Homebox API limitations"**
  for omitting hierarchy info, which is only true for legacy Homebox; in
  entities mode the parent is available, this tool just omits it
  deliberately for a simpler flat view.

### Changed

- Dependency versions are now bounded (`fastmcp>=2.3.4,<3`, `httpx>=0.28.1`,
  `pydantic>=2.10.6`, `starlette>=0.41.0`, `uvicorn>=0.32.0`) to prevent a
  future breaking release from silently breaking the addon on the next
  image rebuild.

### Documentation

- `DOCS.md`/`DOCS-pt-br.md` were missing `homebox_get_location_tree` from the
  tool list entirely, and `README.md`/`README-pt-br.md`'s tool tables covered
  only 7 of the 18 available tools. Both now list all 18.
- The "Testing the Connection" section's `curl`/SSE example stopped working
  after the move to Streamable HTTP (a bare `GET /sse` now correctly returns
  `400 Bad Request` instead of an SSE handshake). Replaced with instructions
  that work against the transport actually in use, recommending the MCP
  Inspector — and fixed its install command, since `@anthropic/mcp-inspector`
  isn't a real package (the official one is `@modelcontextprotocol/inspector`).
- `DOCS-pt-br.md` had drifted out of sync with the current auth flow/code: it
  described automatic token generation on enabling `mcp_auth_enabled` (never
  true — the token must be generated via the dashboard button and copied
  into the config), told users to leave the OAuth Client ID blank (should be
  `mcp` or any text), and its "Authentication Error" troubleshooting section
  still referred to username/password login, removed in 0.3.0 in favor of
  API tokens.

## [0.2.0] - 2026-01-26

### Added

- **New tool**: `homebox_get_location_tree` - Returns complete location hierarchy tree
  - Addresses [Issue #1](https://github.com/oangelo/homebox-mcp/issues/1)
  - Fetches all locations with parent/children relationships
  - Returns nested tree structure for easy hierarchy visualization
- All tool docstrings translated to English

### Changed

- **Internationalization**: Project translated to English
- Dashboard UI now in English
- Documentation in English with Portuguese version available
- Added `README-pt-br.md` and `DOCS-pt-br.md` for Portuguese speakers
- `homebox_list_locations` now documents Homebox API limitation (parent_id always null)

### Fixed

- Documented workaround for Homebox API not returning parent_id in list endpoint

## [0.2.1] - 2026-01-26

### Fixed

- Preserve `parentId` when updating a location without specifying a new parent
  - Prevents accidental loss of hierarchy on location updates

## [0.1.8] - 2026-01-10

### Added

- Support for Basic Authentication (client_id:client_secret)
- Debug logging for Authorization headers
- Better error messages for authentication

### Changed

- Claude.ai now uses OAuth Client ID + Client Secret fields
- Client ID can be any text (e.g., "mcp")
- Client Secret should contain the authentication token

## [0.4.0] - 2026-01-09

### Added

- **Optional OAuth authentication** for the MCP endpoint
- New `mcp_auth_enabled` option to enable/disable authentication
- New `mcp_auth_token` option to set the Bearer token
- Dashboard shows authentication status
- Recommendation: test without auth first, then enable

### How to Use

1. Test the connection with `mcp_auth_enabled: false`
2. After it works, set a token in `mcp_auth_token`
3. Enable `mcp_auth_enabled: true`
4. In Claude.ai, configure: OAuth Client ID = `mcp`, OAuth Client Secret = your token

## [0.3.0] - 2026-01-09

### Changed

- **BREAKING**: Removed email/password authentication (didn't work correctly)
- Now uses only API Token authentication
- Simplified configuration: only `homebox_url`, `homebox_token`, and `log_level`

### How to Migrate

1. In Homebox, go to **Profile** → **API Tokens** → **Create Token**
2. Copy the generated token
3. Configure the addon with the token

## [0.2.2] - 2026-01-09

### Changed

- Dashboard now shows clear instructions for Cloudflare Tunnel configuration
- Internal address (`http://homeassistant:8099`) displayed for tunnel configuration
- Instructions on adding `/sse` to the tunnel address for Claude.ai

### Fixed

- FastMCP API fix: `sse_app()` → `http_app(transport="sse")`

## [0.2.0] - 2026-01-06

### Added

- Web status dashboard on the addon homepage
- Displays connection status with Homebox
- Shows count of locations, items, and labels
- Displays server uptime
- Shows MCP endpoint for easy configuration
- List of available tools in the dashboard
- API endpoint `/api/status` for programmatic queries
- Auto-refresh every 30 seconds

## [0.1.1] - 2026-01-06

### Added

- Port 8099 exposed directly for easier external connection
- Support for direct connection via `http://YOUR_IP:8099/sse`

### Fixed

- Removed deprecated `description` parameter from FastMCP
- Removed Alpine package version pinning

## [0.1.0] - 2026-01-06

### Added

- Initial MCP server with SSE support
- Integration with Homebox API v1
- Tools for location management:
  - `homebox_list_locations`
  - `homebox_get_location`
  - `homebox_create_location`
  - `homebox_update_location`
  - `homebox_delete_location`
- Tools for item management:
  - `homebox_list_items`
  - `homebox_get_item`
  - `homebox_search`
  - `homebox_create_item`
  - `homebox_update_item`
  - `homebox_move_item`
  - `homebox_delete_item`
- Tools for label management:
  - `homebox_list_labels`
  - `homebox_create_label`
  - `homebox_update_label`
  - `homebox_delete_label`
- Statistics tool:
  - `homebox_get_statistics`
- Automatic authentication with token renewal
- Configuration via Home Assistant addon options
- Supported architectures: amd64, aarch64
