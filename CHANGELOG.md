# Changelog

## [2.1.2] - 2026-01-01

### Fixed - Installation State Consistency

**Critical bug fix:**
- Added protection against password mismatch when reinstalling
- Installation now detects inconsistent state (postgres/ exists but .env missing, or vice versa)
- Prevents silent authentication failures caused by mismatched database credentials

**Documentation and metadata fixes:**
- Updated pinokio.json description: SQLite → PostgreSQL
- Fixed start.js comment: "Flask server" → "API server" (server.py uses http.server, not Flask)
- Added troubleshooting section for password mismatch errors

**Version consistency:**
- All version references now aligned to 2.1.2

---

## [2.1.1] - 2025-12-31

### Changed - PostgreSQL Database Backend

This version replaces SQLite with PostgreSQL for improved reliability and performance.

**What's new:**
- Portable PostgreSQL 16.1 installation (no system-wide install needed)
- Automatic PostgreSQL download and initialization during install
- `.env` file generation with secure database credentials
- `start_postgres.py` script for reliable database startup
- PostgreSQL starts automatically before LiteLLM

**Technical changes:**
- `install.js`: Added PostgreSQL download, extraction, and initialization
- `start.js`: Added PostgreSQL startup step before LiteLLM
- `config.yaml`: Changed `database_url` from SQLite to `env/DATABASE_URL`
- `.gitignore`: Added `postgres/` directory
- New file: `start_postgres.py` for database startup management
- New file: `.env` with `DATABASE_URL` and `LITELLM_MASTER_KEY`

**Breaking changes:**
- Existing SQLite databases (`litellm.db`) will not be migrated
- Fresh installation required for existing users

**Upgrade notes:**
- Delete `litellm.db` before upgrading
- Run fresh install to download PostgreSQL
- Reconfigure provider accounts after upgrade

---

## [2.1.0] - 2025-12-31

### Added - True Model Emulation

This version implements **true model name emulation** using LiteLLM's database-backed model management.

**What's new:**
- SQLite database integration via Prisma ORM
- Dynamic model registration using `/model/new` API
- True model name translation/interception
- Emulated models persist across restarts

**How emulation works:**
1. Connect provider accounts (stores API keys)
2. Configure emulation (which model to call, what name to use)
3. Start emulator (registers mapping in database)
4. Apps request emulated name (e.g., "gpt-4")
5. LiteLLM routes to actual model (e.g., "groq/llama-3.3-70b-versatile")

**Technical changes:**
- Added SQLite database: `file:./litellm.db`
- Removed static config.yaml regeneration
- Implemented `/model/new` API integration
- Rewrote `/emulator/start` and `/emulator/stop` endpoints
- Wildcard routes now managed via database instead of config.yaml
- Added `add_wildcard_to_database()` and `remove_wildcard_from_database()` functions
- Removed `regenerate_config_yaml()` and `restart_litellm()` functions
- Added Prisma dependency to install.js

**Breaking changes:**
- None - wildcard passthrough still works identically
- Database file `litellm.db` will be created on first run

**Upgrade notes:**
- Existing provider accounts are preserved
- Wildcard routes will be re-registered in database on first connection
- No manual migration needed

---

## [2.0.0] - 2025-12-30

### Released - Wildcard Provider Passthrough

This version is a **wildcard provider passthrough system**. The "emulation" features shown in the UI are not yet functional.

**What actually works:**
- LiteLLM proxy with wildcard routes (groq/*, deepseek/*, etc.)
- Provider account management with API key storage
- config.yaml generation with wildcard providers
- All models from connected providers exposed via OpenAI-compatible endpoint

**Known limitations (non-functional features):**
- `/emulator/start` endpoint (server.py line ~275) returns success but doesn't create model mappings
- "Emulated Model Name" UI field does nothing
- Cannot make apps request "gpt-4" and route to a different model
- System is passthrough only - requests go directly to whatever model name is specified

**Why emulation doesn't work:**
- Requires PostgreSQL or SQLite database with Prisma ORM
- Requires LiteLLM's `/model/new` API with `STORE_MODEL_IN_DB=True`
- Current architecture uses static config.yaml with wildcards only

**Next version will implement true emulation:**
- Add database support (PostgreSQL/SQLite + Prisma)
- Implement dynamic model registration via `/model/new` API
- Build actual model name translation/interception
- Complete backend rewrite in server.py

This release provides stable wildcard passthrough for multi-provider access.

## [2.0.0-beta.8] - 2025-12-29

### Fixed
- **Critical**: Added SQLite database configuration for LiteLLM dynamic model management
  - Without `database_url`, `/model/new` and `/model/delete` API calls fail with 500 errors
  - Added `database_url: "sqlite:///./litellm.db"` to generated config.yaml
- **Critical**: Added Prisma installation and generation to install.js
  - LiteLLM's database features require Prisma ORM
  - Install script now runs `pip install prisma` and `prisma generate` with correct schema path
- **Status logic**: Emulator no longer shows "Running" on startup before any configuration
  - Now correctly distinguishes between wildcard passthrough models (e.g., `groq/*`) and explicit emulations
  - Status only shows "Running" when user has started an explicit model mapping
- **Accounts refresh button**: Now actually reloads and repopulates accounts from server
  - Previously called API but didn't update the UI with new accounts
- **Stop button validation**: Removed incorrect "Select a model first" error when stopping
  - Validation now only applies when starting, not stopping
- **Model deletion**: Now uses correct `model_info.id` instead of `model_name` for `/model/delete` API
- **Emulator stop**: Now only deletes explicitly configured emulations, preserving wildcard models

### Changed
- Models in dropdown now sorted alphabetically
- Emulated model names dropdown now sorted alphabetically
- `/emulator/stop` only removes user-configured models, not wildcard passthroughs

### Added
- `is_wildcard_model()` helper to identify passthrough models
- `get_active_emulations()` helper to filter out wildcards from model list

## [2.0.0-beta.7] - 2025-12-28

### Changed
- Updated provider list to 9 specific providers: AI/ML API, Bytez, Cerebras, Cloudflare Workers AI, DeepSeek, Google Gemini, Groq, Hugging Face, OpenRouter
- All dropdowns now sorted alphabetically
- Provider dropdown in connect.html now uses search-as-you-type (matches config.html)
- Added refresh button for accounts dropdown in config.html

### Added
- `/emulator/active` endpoint to show currently running emulated models

### Fixed
- Models added dynamically via `/model/new` when emulator starts
- Removed LiteLLM SDK dependency from server.py (uses only proxy HTTP endpoints)

## [2.0.0-beta.6] - 2025-12-27

### Changed
- Restored original UI design (config.html and connect.html)
- New backend server (`server.py`) provides all API endpoints
- Server stores accounts in `config/accounts.json` (server-side, not browser)
- Server proxies model operations to LiteLLM
- Uses `litellm[proxy]` package (includes all proxy dependencies like `backoff`)
- Updated pinokio.js to version 5.3.0 with Connect and Emulator tabs

### Architecture
- `server.py` (port 8765) - API server + static file serving
- LiteLLM proxy (port 11434) - model routing
- API endpoints: /providers/*, /config/*, /emulator/*, /health, /models

### Security
- API keys stored server-side in `config/accounts.json`
- Keys never stored in browser localStorage
- Keys sent to LiteLLM when starting emulator

### Fixed
- `ModuleNotFoundError: No module named 'backoff'` - now uses `litellm[proxy]`

## [2.0.0-beta.5] - 2025-12-26

### Fixed
- Removed pip install from start.json (now only in install.json)
- Fixed ModuleNotFoundError on first launch
- Fixed LiteLLM proxy startup failures (port conflicts, missing error logs)
- Fixed UI bugs: tab disconnect, unresponsive stop button, no error display
- Models now fetched live from LiteLLM instead of hardcoded arrays

### Removed
- PROVIDER_REGISTRY - replaced with LiteLLM /v1/models endpoint
- Navigation links between emulator and connect pages
- "Connected Providers" collapsible section from emulator page
- "No accounts connected" warning boxes
- Security message boxes
- Unnecessary UI features not requested

### Changed
- Models cached in memory (cleared on restart/provider change/manual refresh)
- App now only: manages accounts, generates config, starts/stops LiteLLM
- All provider/model info fetched from LiteLLM

## [2.0.0-beta.4] - 2025-12-25

### Fixed
- **BREAKING**: Corrected architecture to use LiteLLM proxy server instead of custom routing
- Removed redundant routing code (litellm_client.py, openai_adapter.py)
- Simplified backend to config generator + subprocess manager

### Changed
- LiteLLM now runs as a subprocess managed by FastAPI
- All routing/provider logic handled by LiteLLM proxy
- App only generates `config/config.yaml` + manages process lifecycle
- Connect UI now only shows cards for providers with saved accounts
- API keys now encrypted with Fernet before storage
- Environment variable pattern: `{PROVIDER}_{ACCOUNTNAME}` (e.g., `OPENROUTER_PERSONAL`)
- Add Provider modal with Provider dropdown (searchable), Account Name, API Key fields
- Provider cards show "Add" button and "Edit" mode with checkboxes for bulk delete

### Removed
- `server/litellm_client.py` - replaced by LiteLLM proxy
- `server/openai_adapter.py` - replaced by LiteLLM proxy
- `server/logger.py` - use LiteLLM's logging
- Duplicate documentation files: `QWEN.md`, `GEMINI.md`, `AGENTS.md`
- Unused files: `ENVIRONMENT`, `test-connect.py`, `test-connect.json`, `stop.json`
- `tests/` directory

### Added
- `cryptography` dependency for API key encryption
- `config/.secret` file for encryption key (gitignored)
- `config/config.yaml` generation for LiteLLM (gitignored)
- LiteLLM subprocess management in main.py

## [2.0.0-beta.3] - 2025-12-19

### Added
- **Connect tab** in Pinokio interface - separate HTML page (`public/connect.html`) for account management
- **Account-based credential system** - Users can save multiple accounts per provider
  - Example: "Personal (Anthropic)", "Work (OpenAI)", "Gmail (Google)"
  - Accounts stored locally in `config/accounts.json`
- **Emulated model name dropdown** with 18 popular models + custom option
  - Popular models: gpt-4, gpt-4-turbo, gpt-3.5-turbo, claude-3-opus, claude-3-sonnet, claude-3-haiku, llama3-70b, llama3-8b, llama3.1-405b, mistral-large, mistral-medium, mixtral-8x7b, gemini-pro, gemini-1.5-pro, command-r-plus, command-r, deepseek-coder, qwen-72b
  - Custom option allows entering any model name
- `/providers/accounts` endpoint - List all saved accounts (without exposing API keys)
- `/providers/connect` endpoint - Save API key with account name
- `/providers/disconnect` endpoint - Remove specific account
- `/providers/models` endpoint - Get models for specific account/provider
- Third menu button in Pinokio interface: Connect | Emulator | Update
- **Four-step configuration UI** with numbered steps:
  1. Account - Which credential to use
  2. Provider - The actual AI provider
  3. Real Model - The actual model to use
  4. Emulated Model Name - What Pinokio apps will request

### Changed
- Configuration UI restructured with proper hierarchy (Account first, then Provider, Model, Emulated Name)
- Account dropdown shows all saved accounts with provider labels
- Provider dropdown filtered by selected account
- Emulated name changed from free text input to dropdown with popular options + custom
- `get_api_key()` now supports priority order: account key > env var > any saved account
- `chat()` function accepts `account` parameter for credential lookup
- Removed endpoint display from UI (localhost:11434 not shown to user)
- `/config/state` now includes `accounts` list
- `/emulator/status` now includes `account` field in currentConfig

### Fixed
- **Architecture corrected**: Now properly emulates model names with account-based credentials
  - Previous beta.2 used environment variables only for API keys
  - Beta.3 allows UI-based credential management via Connect tab
- Dynamic provider detection now checks both saved accounts AND environment variables

## [2.0.0-beta.2] - 2025-12-19

### Fixed
- **BREAKING**: Corrected architecture to implement true model name emulation
- Removed concept of hardcoded-only provider lists - now uses dynamic detection
- Fixed status indicators to distinguish between provider connectivity and emulator state
- Providers are now shown based on API key availability in environment

### Added
- **Model Name Emulation**: Configure `emulatedModelName` to make Pinokio apps believe they're using one model while actually routing to another
- **Connect Section**: Collapsible UI section showing all providers and their connection status (API key present/missing)
- **`/emulator/status` endpoint**: Comprehensive status check that returns:
  - `emulatorRunning`: Whether emulator is actively routing requests
  - `providerOnline`: Whether configured provider is reachable
  - `currentConfig`: Full configuration including emulated model name
- **Dynamic Provider Detection**: `get_available_providers()` and `get_all_providers_with_status()` functions
- **Provider cards**: Visual cards showing each provider's connection status
- **Separate status indicators**: Clear distinction between "Provider Online" and "Emulator Running"
- `emulatedModelName` field in configuration schema
- `is_provider_configured()` function for checking API key availability
- Model name validation in request handler (if emulated name is set, request must match)

### Changed
- Configuration UI now includes "Emulated Model Name" input field
- Provider dropdown labels updated to "Real Provider" for clarity
- Model dropdown labels updated to "Real Model" for clarity
- Status refresh now uses `/emulator/status` instead of just `/health`
- `start_emulator()` now accepts `emulated_model_name` parameter
- Presets now save and restore `emulatedModelName`
- `SUPPORTED_PROVIDERS` renamed to `PROVIDER_REGISTRY` (alias kept for backward compatibility)
- `list_providers()` now includes `connected` field in response
- Version bumped to 2.0.0-beta.2

### Architecture Changes
- When `emulatedModelName` is configured:
  - Incoming requests MUST use that exact model name or receive 404 error
  - Response returns the emulated model name (not the real provider's model)
- When `emulatedModelName` is empty (backward compatible):
  - Any model name is accepted
  - Response returns the requested model name
- Dynamic provider list: UI shows all providers but indicates which have API keys

## [2.0.0-beta.1] - 2025-12-19

### Breaking Changes
- **BREAKING**: Replaced Puter OAuth with LiteLLM API key authentication
- **BREAKING**: Config schema changed - `backend`/`puterModel`/`spoofedOpenAIModelId` replaced with `provider`/`model`/`apiKeyEnvVar`
- **BREAKING**: Removed Node.js - now uses Python/FastAPI

### Added
- Multi-provider support via LiteLLM (100+ providers)
- API key-based authentication
- Support for OpenAI, Anthropic, Groq, Mistral, Google Gemini, Cohere, Together AI, OpenRouter, DeepSeek, Cerebras
- Provider dropdown in UI
- API key environment variable configuration
- Test Connection button for verifying API keys
- `/providers` endpoint to list supported providers
- `.env.example` template for API key configuration
- Python requirements.txt
- pytest test suite

### Changed
- Project renamed to "Virtual Model Emulator"
- Server rewritten from Node.js/Express to Python/FastAPI
- UI updated for provider/model/API key selection
- Pinokio install.json and start.json updated for Python

### Removed
- Puter.js integration
- Puter OAuth authentication
- Single-provider limitation
- "Spoofed model ID" concept (no longer needed)
- Node.js dependencies (package.json, package-lock.json)

## [1.0.0] - 2025-12-14

### Added
- OpenAI-compatible endpoint for Puter AI
- Searchable model dropdowns
- Configuration presets
- Auto-start workflow in Pinokio
