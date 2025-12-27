# Changelog

## [2.0.0-beta.6] - 2025-12-27

### Breaking Changes
- **BREAKING**: Removed custom FastAPI server - now runs LiteLLM proxy directly
- **BREAKING**: Removed Connect tab and accounts system - API keys entered when adding models
- **BREAKING**: Removed API key encryption - keys sent directly to LiteLLM (stored server-side)

### Added
- Simple static file server (`server.py`) for serving UI
- Provider dropdown with links to get API keys
- API key input field when adding models (not stored in browser)

### Changed
- Architecture simplified: just LiteLLM proxy + static file server
- `config.html` completely rewritten for direct LiteLLM API calls
- Uses `litellm[proxy]` package (includes all proxy dependencies like `backoff`)
- API keys sent directly to LiteLLM `/model/new` endpoint, never stored in localStorage
- 4-step flow: Provider → Model → API Key → Emulated Name

### Removed
- `server/` directory (main.py, config.py) - no longer needed
- `public/connect.html` - accounts system removed
- `config/` directory (accounts.json, .secret, saved-configs.json)
- Fernet encryption system - LiteLLM handles key storage
- Account-based credential management
- All custom API endpoints (/providers/*, /emulator/*, /config/*)

### Security
- API keys no longer stored in browser localStorage
- Keys entered per-model and sent directly to LiteLLM server-side storage

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
