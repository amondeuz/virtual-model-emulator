# Virtual Model Emulator v2.0.0

A Pinokio app that provides a local OpenAI-compatible HTTP endpoint with **model name emulation** powered by LiteLLM proxy server. Route any model name to any provider - make Pinokio apps think they're talking to one model while actually using another.

## What is this?

A **model name emulator** that translates model names for Pinokio applications. Configure your preferred provider and model, set an emulated model name, and Pinokio apps will believe they're using that model while actually getting responses from your configured provider.

**Example**: Configure the emulator to respond to `gpt-4` requests while actually routing them to DeepSeek or Groq.

## Known Limitations

**This release (2.0.0) is a wildcard passthrough, not a true emulator.**

The UI shows "Emulated Model Name" configuration, but this feature is not yet functional. Here's what actually happens:

✅ **What works:**
- Wildcard provider routing (e.g., `groq/*`, `cerebras/*`, `deepseek/*`)
- All models from connected providers are exposed
- OpenAI-compatible endpoint at localhost:11434
- Provider account management with secure API key storage

❌ **What doesn't work:**
- True model name emulation/translation
- The `/emulator/start` endpoint returns success but doesn't implement mapping
- You cannot make apps request "gpt-4" and have it route to a different model
- The "Emulated Model Name" field in Step 4 has no effect

**Why:** Implementing true emulation requires a database (PostgreSQL or SQLite) with Prisma ORM to use LiteLLM's `/model/new` API for dynamic model registration. The current architecture uses static config.yaml with wildcard routes.

**Roadmap for v2.1.0:**
- Add database support with Prisma
- Implement `/model/new` API integration
- Build true model name translation
- Complete server.py backend rewrite

**Current use case:** If you need multi-provider access through a unified endpoint with wildcard routing, this release works perfectly. If you specifically need model name emulation, wait for v2.1.0.

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
├── server.py             # Backend API server + static file serving
├── start.js              # Pinokio start script
├── install.js            # Pinokio install script
├── pinokio.js            # Pinokio app definition (v5.3.0)
├── config.yaml           # LiteLLM config (generated)
├── requirements.txt      # Python dependencies (litellm[proxy])
├── CHANGELOG.md          # Version history
└── README.md             # This file
```

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
