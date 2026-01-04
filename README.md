# Virtual Model Emulator v2.1.4

A unified AI model emulation and routing platform that allows you to transparently route API calls to different LLM providers while presenting them as if they're a single model.

## Features

- **Multi-Provider Support**: Route to 90+ AI providers (OpenAI, Anthropic, Groq, Mistral, etc.)
- **Model Aliasing**: Request "gpt-4" but route to any provider's model
- **Local-First Architecture**: Run entirely on your machine, no cloud dependencies
- **PostgreSQL-Based Configuration**: Persistent provider and model settings
- **Web-Based UI**: User-friendly interface for managing configurations
- **Cross-Tab Synchronization**: Real-time updates across browser tabs in Pinokio

## Quick Start

### Prerequisites
- Windows 10+ (macOS/Linux supported with manual setup)
- Python 3.9+
- 64GB RAM recommended
- NVIDIA RTX 3060 or better (optional, for local inference)

### Installation

1. **Download Pinokio**: https://pinokio.co/
2. **Install Virtual Model Emulator**:
   - Open Pinokio → Click "Discover" → Search "Virtual Model Emulator" → Click "Install"
3. **Start the App**:
   - Click "Start" in Pinokio
   - Wait for all services to initialize (~20 seconds)
   - Click the UI link or go to http://localhost:8775/config.html

### First Time Setup

1. **Add API Keys**: Click "Manage API Keys" tab
   - Select provider (OpenAI, Anthropic, Groq, etc.)
   - Paste your API key
   - Click "Connect"

2. **Configure Models**: Click "Configuration" tab
   - Select account and model
   - Enter emulated name
   - Click "Start Emulation"

3. **Use the API**:
   - Your app now calls http://localhost:11435/v1/chat/completions
   - Requests are routed to your configured provider

## Architecture

Three services run together:

- **PostgreSQL** (port 5450+): Stores accounts and configurations
- **LiteLLM Proxy** (port 11435): Routes API calls to providers
- **API Server** (port 8775): Serves web UI and management endpoints

## Supported Providers

90+ providers including:
- OpenAI (gpt-3.5, gpt-4, etc.)
- Anthropic (Claude models)
- Google (Gemini)
- Groq (Llama inference)
- Mistral
- Meta (Llama)
- And 80+ more

## Troubleshooting

### "Can't connect to database"
- Check if PostgreSQL is running: `pg_isready -p 5432`
- Delete `.env` file and reinstall to reset

### "LiteLLM not responding"
- Check: http://localhost:11435/health
- Restart the app from Pinokio

### "Models aren't updating"
- The app auto-syncs across tabs (BroadcastChannel)
- On older browsers, manually refresh the Configuration tab
- Or wait 10 seconds for polling to detect change

## Version History

- **v2.1.4** (2025-01-04): Complete architectural refactor, UI fixes, cross-tab sync
- **v2.1.2**: Previous version
- **v2.0.0**: Initial release

## Security

- API keys stored locally in PostgreSQL
- No data sent to external servers except to your selected provider
- Keep your `.env` file secure

For full documentation, see ARCHITECTURE.md and INSTALL_NOTES.md
