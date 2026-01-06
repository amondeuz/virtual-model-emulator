# Virtual Model Emulator v2.2.1

A unified AI model emulation and routing platform that allows you to transparently route API calls to different LLM providers while presenting them as if they're a single model.

## Features

- **Multi-Provider Support**: Route to 100+ AI providers (OpenAI, Anthropic, Groq, Mistral, etc.)
- **Model Aliasing**: Request "gpt-4" but route to any provider's model
- **Local-First Architecture**: Run entirely on your machine, no cloud dependencies
- **Direct SDK Integration**: Uses LiteLLM SDK directly (no proxy server needed)
- **Web-Based UI**: User-friendly interface for managing configurations
- **Cross-Tab Synchronization**: Real-time updates across browser tabs in Pinokio
- **Fast Startup**: Single service architecture for quick initialization

## Quick Start

### Prerequisites
- Windows 10+ (macOS/Linux supported)
- Python 3.9+

### Installation

1. **Download Pinokio**: https://pinokio.computer/
2. **Install Virtual Model Emulator**:
   - Open Pinokio → Click "Discover" → Search "Virtual Model Emulator" → Click "Install"
3. **Start the App**:
   - Click "Start" in Pinokio
   - Wait for the service to initialize (~5 seconds)
   - Click the UI link or go to http://localhost:8775/config.html

### First Time Setup

1. **Add API Keys**: Click "Manage API Keys" tab
   - Select provider (OpenAI, Anthropic, Groq, etc.)
   - Paste your API key
   - Click "Connect"

2. **Configure Models**: Click "Configuration" tab
   - Select account and model
   - Enter emulated name (e.g., "gpt-4")
   - Click "Start Emulation"

3. **Use the API**:
   - Your app now calls http://localhost:8775/v1/chat/completions
   - Requests are routed to your configured provider

## Architecture

Single service design using LiteLLM SDK directly:

```
API Server (port 8775)
    ↓ uses LiteLLM SDK
Provider APIs (OpenAI, Anthropic, etc.)
```

- **API Server** (port 8775): Serves web UI, management endpoints, and chat completions
- **LiteLLM SDK**: Handles provider routing and API translation (in-process)
- **JSON Storage**: Accounts and emulations stored locally

## Supported Providers

11+ providers including:
- OpenAI (gpt-4o, gpt-4, gpt-3.5-turbo, etc.)
- Anthropic (Claude 3.5, Claude 3)
- Google (Gemini 2.0, 1.5)
- Groq (Llama 3.3, Mixtral)
- Mistral (mistral-large, mixtral)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Together AI (Llama, Qwen)
- OpenRouter (100+ models)
- And more...

## API Usage

### Chat Completions

```bash
curl http://localhost:8775/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

The emulator will route "gpt-4" to whatever model you configured.

## Troubleshooting

### "Server not responding"
- Check: http://localhost:8775/health
- Restart the app from Pinokio

### "No API key found"
- Ensure you've added an API key for the provider in the "Manage API Keys" tab
- Check that the emulation is configured in the "Configuration" tab

### "Models aren't updating"
- The app auto-syncs across tabs (BroadcastChannel)
- On older browsers, manually refresh the Configuration tab

## Version History

- **v2.2.1** (2026-01-06): Production hardening - rate limiting, caching, audit logging, key rotation
- **v2.2.0** (2025-01-06): Major simplification - removed proxy/database, uses SDK directly
- **v2.1.4** (2025-01-04): Complete architectural refactor, UI fixes, cross-tab sync
- **v2.1.2**: Previous version
- **v2.0.0**: Initial release

## Security

- API keys stored locally in JSON file
- No data sent to external servers except to your selected provider
- Keep your `config/` directory secure

## Migration from v2.1.x

If upgrading from v2.1.x:
1. Your existing accounts in `config/accounts.json` will continue to work
2. API endpoint changed from port 11435 to 8775
3. No PostgreSQL needed - you can delete the `postgres/` directory if present

For full documentation, see ARCHITECTURE.md and CHANGELOG.md
