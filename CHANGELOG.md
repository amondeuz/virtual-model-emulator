# Changelog

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
