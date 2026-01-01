# Virtual Model Emulator v2.1.2

A Pinokio app that provides a local OpenAI-compatible HTTP endpoint with **true model name emulation** powered by LiteLLM proxy server and PostgreSQL database. Route any model name to any provider - make Pinokio apps think they're talking to one model while actually using another.

## What is this?

A **model name emulator** that translates model names for Pinokio applications. Configure your preferred provider and model, set an emulated model name, and Pinokio apps will believe they're using that model while actually getting responses from your configured provider.

**Example**: Configure the emulator to respond to `gpt-4` requests while actually routing them to DeepSeek or Groq.

## Features (v2.1.2)

### ✅ What Works

**Wildcard Provider Routing:**
- Connect provider accounts with API keys
- Automatic wildcard routes (groq/*, cerebras/*, etc.)
- All models from connected providers exposed
- OpenAI-compatible endpoint at localhost:11434

**True Model Name Emulation:**
- Configure which model to call and what name to use
- Apps request emulated name (e.g., "gpt-4")
- LiteLLM routes to actual model (e.g., "groq/llama-3.3-70b-versatile")
- Emulations persist across restarts (stored in database)
- Multiple emulations can be active simultaneously

**Database-Backed Configuration:**
- PostgreSQL database for persistent model registration
- Portable PostgreSQL installation (no system-wide install needed)
- No restarts required when adding/removing models
- Configuration survives app restarts

### 🔧 How It Works

**Architecture:**
1. **Provider Accounts** → Store API keys securely
2. **Wildcard Routes** → Added to database when provider connected
3. **Model Emulation** → Explicit name mappings via `/model/new` API
4. **LiteLLM Proxy** → Intercepts requests and routes to correct provider

**Example Flow:**
```
App requests "gpt-4"
  ↓
LiteLLM checks database
  ↓
Finds mapping: "gpt-4" → "groq/llama-3.3-70b-versatile"
  ↓
Routes to Groq API with API key from connected account
  ↓
Returns response to app
```

## Quick Start - Emulation

**1. Connect a Provider**
- Click "Connect" on any provider card
- Enter your API key
- Provider shows "Online" with green status

**2. Configure Emulation**
- Step 1: Select Account (choose connected provider account)
- Step 2: Select Provider (e.g., Groq)
- Step 3: Select Model (e.g., llama-3.3-70b-versatile)
- Step 4: Emulated Model Name (e.g., gpt-4)

**3. Start Emulator**
- Click "Start Emulator"
- Status shows "Active emulation: gpt-4 → groq/llama-3.3-70b-versatile"

**4. Use in Your App**
```python
import openai

client = openai.OpenAI(
    api_key="anything",
    base_url="http://localhost:11434/v1"
)

# Request "gpt-4" but actually gets Groq's Llama model
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

**5. Stop Emulator**
- Click "Stop Emulator" to remove emulation
- Wildcard routes remain active

## Architecture

This app runs **LiteLLM as a proxy server** directly:

```
Request Flow:
┌─────────────────────┐
│ Pinokio App         │
│ requests "llama3"   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ LiteLLM Proxy       │
│ (localhost:11434)   │
│                     │
│ Routes "llama3" to  │
│ anthropic/claude-3  │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Response returned   │
│ as "llama3"         │
└─────────────────────┘
```

### Key Features

- **LiteLLM Proxy**: Runs LiteLLM as the model routing engine
- **Two-Page UI**: Connect page for accounts, Emulator page for model configuration
- **Secure Key Handling**: API keys stored server-side, never in browser localStorage
- **4-Step Configuration**: Account → Provider → Model → Emulated Name
- **OpenAI-Compatible Endpoint**: LiteLLM serves at `/v1/chat/completions`
- **9 Providers**: AI/ML API, Bytez, Cerebras, Cloudflare, DeepSeek, Gemini, Groq, Hugging Face, OpenRouter

## Installation

### Via Pinokio (Recommended)

1. Open Pinokio
2. Navigate to the "Discover" tab
3. Search for "Virtual Model Emulator" or paste the repository URL
4. Click "Install"

The app will automatically:
- Create Python virtual environment
- Install LiteLLM with proxy dependencies
- Generate config.yaml with master key

### Manual Installation

```bash
git clone https://github.com/amondeuz/virtual-model-emulator.git
cd virtual-model-emulator
pip install -r requirements.txt
litellm --config config.yaml --port 11434 --host 127.0.0.1
```

## Configuration

### Connect Page

Access the Connect page to manage provider accounts:
```
http://localhost:8765/connect.html
```

Add your API keys here - they're stored securely on the server, not in your browser.

### Emulator Page

Access the Emulator configuration at:
```
http://localhost:8765/config.html
```

**4-Step Configuration:**
1. **Account** - Select which saved account/credential to use
2. **Provider** - The AI provider (auto-filtered by account)
3. **Model** - The actual model from that provider
4. **Emulated Model Name** - What Pinokio apps will request

### Workflow

1. **Open Connect page** via Pinokio menu
2. **Add provider accounts** with your API keys
3. **Open Emulator page** via Pinokio menu
4. **Select an account** from the dropdown
5. **Choose a model** from the provider
6. **Set an emulated model name** (e.g., "gpt-4")
7. Click **Start** to begin routing
8. Configure your Pinokio app to use the emulated model name

## Usage

### Model Name Emulation

```
Pinokio app requests: model="llama3"
                ↓
LiteLLM Proxy: finds llama3 → anthropic/claude-3-5-sonnet
                ↓
Routes to: Anthropic Claude 3.5 Sonnet
                ↓
Returns response: model="llama3" (Pinokio thinks it talked to llama3)
```

### Using the Endpoint

Point any OpenAI-compatible application to:
```
http://localhost:11434/v1/chat/completions
```

**Example: curl**
```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

**Example: Python**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="not-needed"  # API key is configured on the server
)

response = client.chat.completions.create(
    model="llama3",  # Use the emulated model name
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## Supported Providers

| Provider | Prefix | Example Models |
|----------|--------|----------------|
| AI/ML API | `aiml_api/` | Various models via aimlapi.com |
| Bytez | `bytez/` | Models via bytez.com |
| Cerebras | `cerebras/` | llama3.1-8b, llama3.1-70b |
| Cloudflare Workers AI | `cloudflare/` | @cf/meta/llama-3-8b-instruct |
| DeepSeek | `deepseek/` | deepseek-chat, deepseek-coder |
| Google Gemini | `gemini/` | gemini-1.5-pro, gemini-2.0-flash |
| Groq | `groq/` | llama-3.3-70b-versatile, mixtral-8x7b |
| Hugging Face | `huggingface/` | Various open models |
| OpenRouter | `openrouter/` | Any model via OpenRouter |

## File Structure

```
/virtual-model-emulator
├── public/
│   ├── config.html       # Emulator configuration UI
│   └── connect.html      # Provider account management UI
├── config/
│   └── accounts.json     # Saved accounts (server-side, gitignored)
├── postgres/             # PostgreSQL installation (gitignored)
│   ├── bin/              # PostgreSQL binaries
│   └── data/             # Database data files
├── server.py             # Backend API server + static file serving
├── start_postgres.py     # PostgreSQL startup script
├── start.js              # Pinokio start script
├── install.js            # Pinokio install script
├── pinokio.js            # Pinokio app definition (v5.3.0)
├── config.yaml           # LiteLLM config (generated)
├── .env                  # Database credentials (generated, gitignored)
├── requirements.txt      # Python dependencies (litellm[proxy])
├── CHANGELOG.md          # Version history
└── README.md             # This file
```

## Database Storage

PostgreSQL database is installed locally in the `postgres/` directory with data at:
```
postgres/data/
```

The `litellm` database contains:
- Model registrations (wildcards + emulations)
- Active emulation configurations
- Internal LiteLLM proxy state

**Persistence**: Emulations and wildcards survive app restarts.

**Backup**: To preserve your configuration across reinstalls, backup the entire `postgres/data/` directory.

**Reset**: Delete the `postgres/` directory and reinstall to start fresh.

## Security

- **API keys stored server-side** in `config/accounts.json` (gitignored)
- **Keys never stored in browser** localStorage or cookies
- **Master key** protects LiteLLM admin endpoints
- **Nothing leaves your machine** except authorized API requests to providers

## LiteLLM Endpoints

The LiteLLM proxy exposes these endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /model/info` | List configured models |
| `POST /model/new` | Add a new model |
| `POST /model/delete` | Remove a model |
| `POST /v1/chat/completions` | OpenAI-compatible chat |
| `/ui` | LiteLLM Admin UI (optional) |

## Troubleshooting

**LiteLLM proxy won't start**
- Check if port 11434 is in use: `netstat -an | grep 11434`
- Check the Pinokio logs for error messages

**"No module named 'backoff'" error**
- Ensure `litellm[proxy]` is installed, not just `litellm`
- Reinstall: `pip install 'litellm[proxy]'`

**"Unable to connect to database" error on startup**
1. Check if PostgreSQL is running: `postgres\bin\pg_ctl.exe status -D postgres\data`
2. If not running: `python start_postgres.py`
3. Verify `.env` file exists with DATABASE_URL
4. Restart the app

**PostgreSQL won't start**
1. Check if port 5432 is in use: `netstat -an | grep 5432`
2. Check `postgres/logfile` for error messages
3. Try reinitializing: delete `postgres/data` and run install again

**"PostgreSQL directory exists but .env file is missing" or vice versa**
- This error prevents password mismatch issues between PostgreSQL and .env
- If you deleted only one of these (postgres/ or .env), delete the other as well
- Then run the install again for a fresh setup with matching credentials

**"Migration failed" error on startup**
1. Stop the app
2. Stop PostgreSQL: `postgres\bin\pg_ctl.exe stop -D postgres\data`
3. Backup `postgres/data/` (if you want to preserve data)
4. Delete the `postgres/` directory
5. Reinstall the app (fresh database will be created)
6. Reconnect providers and reconfigure emulations

**Emulation not working after restart**
1. Check `/emulator/status` endpoint shows emulator running
2. Verify PostgreSQL is running: `python start_postgres.py`
3. Try stopping and restarting the emulation
4. If issue persists, reset the database and reconfigure

**Models not appearing**
- Click the refresh button next to LiteLLM status
- Check that LiteLLM is running (green indicator)

**Provider not working**
- Verify your API key is correct
- Check that the provider supports the selected model
- Try the model in the provider's own interface first

## Resources

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM Proxy Config](https://docs.litellm.ai/docs/simple_proxy)
- [Pinokio Documentation](https://docs.pinokio.computer/)

## License

MIT

## Contributing

Feel free to fork and extend for your needs.
