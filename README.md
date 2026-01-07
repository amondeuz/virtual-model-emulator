# Virtual Model Emulator v2.2.2

A unified AI model emulation and routing platform that allows you to transparently route API calls to different LLM providers while presenting them as if they're a single model.

## Features

- **Multi-Provider Support**: Route to 100+ AI providers (OpenAI, Anthropic, Groq, Mistral, etc.)
- **Model Aliasing**: Request "gpt-4" but route to any provider's model
- **Local-First Architecture**: Run entirely on your machine, no cloud dependencies
- **Direct SDK Integration**: Uses LiteLLM SDK directly (no proxy server needed)
- **Encrypted API Keys**: Master key encryption with environment variable support (`VME_MASTER_KEY`)
- **Secure Storage**: API keys encrypted in both accounts and emulations, file permissions enforced (0600)
- **Audit Logging**: Security-relevant actions logged to `config/audit.log`
- **Rate Limiting**: Thread-safe 10 req/s per IP to prevent abuse
- **Smart Caching**: Thread-safe 1-hour TTL cache with stale fallback and timeouts
- **Input Validation**: Temperature, max_tokens, and message structure validation
- **Retry Logic**: Exponential backoff for transient failures on all LiteLLM calls
- **Optional HTTPS**: SSL/TLS support via environment variables
- **Web-Based UI**: User-friendly interface with client-side validation
- **Cross-Tab Synchronization**: Real-time updates across browser tabs in Pinokio
- **Fast Startup**: Single service architecture, 5-second initialization

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

- **v2.2.2** (2026-01-07): Security hardening - 28 fixes including encrypted emulations, environment-based master key, HTTPS support, thread-safe caching, input validation, retry logic
- **v2.2.1** (2026-01-06): Production hardening - rate limiting, caching, audit logging, key rotation
- **v2.2.0** (2025-01-06): Major simplification - removed proxy/database, uses SDK directly
- **v2.1.4** (2025-01-04): Complete architectural refactor, UI fixes, cross-tab sync
- **v2.1.2**: Previous version
- **v2.0.0**: Initial release

## Security

- **Encrypted Storage**: API keys encrypted with Fernet (AES-128-CBC)
- **Environment-Based Keys**: Master key via `VME_MASTER_KEY` environment variable
- **File Permissions**: Sensitive files protected with 0600 permissions
- **Input Validation**: All API inputs validated (temperature, max_tokens, messages)
- **Error Sanitization**: Secrets removed from error messages
- **Optional HTTPS**: TLS support via `SSL_CERT_FILE` and `SSL_KEY_FILE`
- **Localhost CORS**: Cross-origin requests restricted to localhost
- **Admin Authentication**: Management endpoints protected via `ADMIN_SECRET`
- No data sent to external servers except to your selected provider

## Migration from v2.1.x

If upgrading from v2.1.x:
1. Your existing accounts in `config/accounts.json` will continue to work
2. API endpoint changed from port 11435 to 8775
3. No PostgreSQL needed - you can delete the `postgres/` directory if present

For full documentation, see ARCHITECTURE.md and CHANGELOG.md
