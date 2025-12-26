# Virtual Model Emulator v2.0.0-beta.5

A Pinokio app that provides a local OpenAI-compatible HTTP endpoint with **model name emulation** powered by LiteLLM proxy server. Route any model name to any provider - make Pinokio apps think they're talking to one model while actually using another.

## What is this?

A **model name emulator** that translates model names for Pinokio applications. Configure your preferred provider and model, set an emulated model name, and Pinokio apps will believe they're using that model while actually getting responses from your configured provider.

**Example**: Configure the emulator to respond to `llama3` requests while actually routing them to Anthropic Claude 3.5 Sonnet.

## Architecture

This app uses **LiteLLM as a proxy server** (subprocess) for all model routing:

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
│ ┌─────────────────┐ │
│ │ Reads config.yaml │
│ │ model_list:     │ │
│ │  - llama3 →     │ │
│ │    anthropic/   │ │
│ │    claude-3     │ │
│ └────────┬────────┘ │
│          ↓          │
│ Routes to Anthropic │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Response returned   │
│ as "llama3"         │
└─────────────────────┘
```

### Key Features

- **LiteLLM Proxy Server**: All routing handled by LiteLLM subprocess
- **Encrypted API Keys**: Keys encrypted with Fernet before storage
- **Account-Based Credentials**: Save multiple API keys per provider
- **Connect Tab**: Dedicated page for managing provider accounts
- **4-Step Configuration**: Account → Provider → Model → Emulated Name
- **Dynamic Config Generation**: Generates `config/config.yaml` for LiteLLM
- **OpenAI-Compatible Endpoint**: LiteLLM serves at `/v1/chat/completions`
- **100+ Providers**: Access OpenAI, Anthropic, Groq, Mistral, Google Gemini, and more

## Installation

### Via Pinokio (Recommended)

1. Open Pinokio
2. Navigate to the "Discover" tab
3. Search for "Virtual Model Emulator" or paste the repository URL
4. Click "Install"

The app will automatically:
- Install Python dependencies (including `cryptography` for encryption)
- Start the configuration server
- Open the configuration UI

### Manual Installation

```bash
git clone https://github.com/amondeuz/virtual-model-emulator.git
cd virtual-model-emulator
pip install -r requirements.txt
python -m server.main
```

Server starts on `http://localhost:11434` by default.

## Configuration

### API Keys (Connect Tab)

The **Connect** tab provides a UI for managing provider accounts:

1. Open Pinokio and navigate to Virtual Model Emulator
2. Click the **Connect** tab
3. Click **Add Provider Account**
4. Select a **Provider** from the dropdown
5. Enter an **Account Name** (e.g., "Personal", "Work")
6. Paste your **API Key**
7. Click **Save Account**

Benefits:
- API keys are **encrypted** before storage using Fernet encryption
- Manage multiple accounts per provider
- Environment variable pattern: `{PROVIDER}_{ACCOUNTNAME}` (e.g., `OPENROUTER_PERSONAL`)

### Pinokio Interface

The app has three tabs in Pinokio:
- **Connect** - Manage provider accounts and API keys
- **Emulator** - Main configuration (default)
- **Update** - Update from GitHub

### Configuration UI (Emulator Tab)

Access the configuration UI at:
```
http://localhost:11434/config.html
```

**4-Step Configuration:**
1. **Account** - Select which credential to use
2. **Provider** - The actual AI provider
3. **Real Model** - The actual model from that provider
4. **Emulated Model Name** - What Pinokio apps will request

### Workflow

1. **Connect a provider** via the Connect tab
2. **Select an Account** from the dropdown (Step 1)
3. **Provider auto-selects** based on account (Step 2)
4. **Select a model** for that provider (Step 3)
5. **Choose an Emulated Model Name** (Step 4)
6. Click **Start** to activate the emulator
7. Configure your Pinokio app to use the emulated model name
8. Requests are routed through LiteLLM proxy to your real provider

## Usage

### Model Name Emulation

```
Pinokio app requests: model="llama3"
                ↓
LiteLLM Proxy: reads config.yaml, finds llama3 → anthropic/claude-3
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

### Health Check & Status

**Emulator status:**
```bash
curl http://localhost:11434/emulator/status
```

Returns:
```json
{
  "emulatorRunning": true,
  "providerOnline": true,
  "currentConfig": {
    "provider": "anthropic",
    "providerName": "Anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "emulatedModelName": "llama3"
  }
}
```

## Supported Providers

| Provider | Models | Environment Variable Pattern |
|----------|--------|------------------------------|
| OpenAI | GPT-4, GPT-4 Turbo, GPT-4o, o1 | `OPENAI_{ACCOUNT}` |
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus | `ANTHROPIC_{ACCOUNT}` |
| Groq | Llama 3.3 70B, Mixtral 8x7B | `GROQ_{ACCOUNT}` |
| Mistral | Mistral Large, Codestral | `MISTRAL_{ACCOUNT}` |
| Google | Gemini 1.5 Pro, Gemini 2.0 Flash | `GOOGLE_{ACCOUNT}` |
| Cohere | Command R+, Command R | `COHERE_{ACCOUNT}` |
| Together AI | Llama 3.3 70B, Qwen 2.5 72B | `TOGETHER_AI_{ACCOUNT}` |
| OpenRouter | Access to many providers | `OPENROUTER_{ACCOUNT}` |
| DeepSeek | DeepSeek Chat, DeepSeek Coder | `DEEPSEEK_{ACCOUNT}` |
| Cerebras | Llama 3.1 8B, Llama 3.1 70B | `CEREBRAS_{ACCOUNT}` |

## File Structure

```
/virtual-model-emulator
├── server/
│   ├── main.py           # FastAPI server + LiteLLM subprocess manager
│   └── config.py         # Config generation + encryption
├── config/
│   ├── default.json      # User configuration
│   ├── accounts.json     # Encrypted API credentials
│   ├── config.yaml       # Generated LiteLLM config (gitignored)
│   ├── .secret           # Encryption key (gitignored)
│   └── saved-configs.json # Saved presets
├── public/
│   ├── config.html       # Emulator configuration UI
│   └── connect.html      # Provider account management UI
├── pinokio.js            # Pinokio app definition
├── pinokio.json          # Pinokio metadata
├── install.json          # Dependency installation
├── start.json            # Server startup
├── requirements.txt      # Python dependencies
└── .env.example          # API key template
```

## API Endpoints

### Configuration
- `GET /config/state` - Current configuration state
- `POST /config/save` - Save configuration
- `POST /config/savePreset` - Save a preset

### Providers
- `GET /providers` - List all providers with status
- `GET /providers/accounts` - List saved accounts
- `POST /providers/connect` - Save API key (encrypted)
- `POST /providers/disconnect` - Remove account
- `GET /providers/models` - Get models for provider

### Emulator Control
- `POST /emulator/start` - Start LiteLLM proxy
- `POST /emulator/stop` - Stop LiteLLM proxy
- `GET /emulator/status` - Detailed emulator status
- `GET /health` - Health check

### Models
- `GET /models` - List available models

## Security

- **API keys are encrypted** using Fernet symmetric encryption
- Encryption key stored in `config/.secret` (gitignored)
- Keys only decrypted when starting LiteLLM proxy
- Nothing leaves your machine except authorized API requests

## Limitations

1. **Text-Only**: Chat completions only - no images, audio, or file uploads
2. **No Streaming**: Responses returned complete, not streamed (LiteLLM limitation)
3. **No Function Calling**: OpenAI tool/function calling not fully supported

## Troubleshooting

**LiteLLM proxy won't start**
- Check if port 11434 is in use
- Verify `config/config.yaml` was generated
- Check logs for error messages

**Port conflicts**
- App checks if port 11434 is in use before starting
- Error logged if port unavailable

**Encryption issues**
- Delete `config/.secret` to regenerate encryption key
- Ensure `cryptography` package is installed

**Provider not working**
- Verify API key is correct in Connect tab
- Check that the provider supports the selected model

## Resources

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM Proxy Config](https://docs.litellm.ai/docs/simple_proxy)
- [Pinokio Documentation](https://docs.pinokio.computer/)

## License

MIT

## Contributing

Feel free to fork and extend for your needs.
