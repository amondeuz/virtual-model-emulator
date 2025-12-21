# Virtual Model Emulator v2.0.0-beta.3

A Pinokio app that provides a local OpenAI-compatible HTTP endpoint with **model name emulation** powered by LiteLLM. Route any model name to any provider - make Pinokio apps think they're talking to one model while actually using another.

## What is this?

A **model name emulator** that translates model names for Pinokio applications. Configure your preferred provider and model, set an emulated model name, and Pinokio apps will believe they're using that model while actually getting responses from your configured provider.

**Example**: Configure the emulator to respond to `llama3` requests while actually routing them to Anthropic Claude 3.5 Sonnet.

### Key Features

- **Model Name Emulation**: Apps request "llama3" but get Claude, GPT-4, or any other model
- **Account-Based Credentials**: Save multiple API keys per provider (e.g., "Personal", "Work")
- **Connect Tab**: Dedicated page for managing provider accounts and API keys
- **4-Step Configuration**: Account → Provider → Model → Emulated Name
- **Emulated Model Dropdown**: 18 popular models + custom option
- **Dynamic Provider Detection**: Shows providers with saved accounts OR environment keys
- **OpenAI-Compatible Endpoint**: POST to `/v1/chat/completions` just like OpenAI
- **100+ Providers**: Access OpenAI, Anthropic, Groq, Mistral, Google Gemini, Cohere, Together AI, and more
- **Searchable Model Dropdown**: Quick search-as-you-type for models
- **Preset Configurations**: Save and load your favorite configurations
- **Auto-Start Workflow**: Pinokio automatically installs dependencies and starts the server
- **Separate Status Indicators**: Clear distinction between provider connectivity and emulator state
- **Health Monitoring**: Built-in connectivity and emulator status checking

## Installation

### Via Pinokio (Recommended)

1. Open Pinokio
2. Navigate to the "Discover" tab
3. Search for "Virtual Model Emulator" or paste the repository URL
4. Click "Install"

The app will automatically:
- Install Python dependencies
- Start the server
- Open the configuration UI

### Manual Installation

```bash
git clone https://github.com/amondeuz/model-emulator.git
cd model-emulator
pip install -r requirements.txt
python -m server.main
```

Server starts on `http://localhost:11434` by default.

## Configuration

### API Keys (Two Methods)

#### Method 1: Connect Tab (Recommended)

The **Connect** tab provides a UI for managing provider accounts:

1. Open Pinokio and navigate to Virtual Model Emulator
2. Click the **Connect** tab
3. Click **Connect** on your preferred provider
4. Enter an **Account Name** (e.g., "Personal", "Work")
5. Paste your **API Key**
6. Click **Save Account**

Benefits:
- Manage multiple accounts per provider
- No need to edit `.env` files
- Credentials stored securely in `config/accounts.json`

#### Method 2: Environment Variables

Alternatively, create a `.env` file in the project root:

```bash
# Copy from .env.example
cp .env.example .env

# Edit and add your API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
```

Supported environment variables:
- `OPENAI_API_KEY` - OpenAI
- `ANTHROPIC_API_KEY` - Anthropic
- `GROQ_API_KEY` - Groq
- `MISTRAL_API_KEY` - Mistral
- `GEMINI_API_KEY` - Google Gemini
- `COHERE_API_KEY` - Cohere
- `TOGETHER_API_KEY` - Together AI
- `OPENROUTER_API_KEY` - OpenRouter
- `DEEPSEEK_API_KEY` - DeepSeek
- `CEREBRAS_API_KEY` - Cerebras

**Note**: Providers with saved accounts OR environment keys are shown as connected.

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
1. **Account** - Select which credential to use (if multiple per provider)
2. **Provider** - The actual AI provider (filtered by account)
3. **Real Model** - The actual model from that provider
4. **Emulated Model Name** - What Pinokio apps will request (dropdown with 18 popular models + custom)

**Additional Features:**
- **Connected Providers**: Collapsible section showing provider status
- **Presets**: Save configurations for quick switching
- **Test Connection**: Verify your API key works before starting
- **Status Indicators**: Separate indicators for provider connectivity and emulator state

### Workflow

1. **Connect a provider** (if not already done via Connect tab or .env)
2. **Select an Account** from the dropdown (Step 1)
3. **Provider auto-selects** based on account (Step 2)
4. **Select a model** for that provider (Step 3)
5. **Choose an Emulated Model Name** from dropdown or enter custom (Step 4)
6. Click **Start** to activate the emulator
7. Configure your Pinokio app to use the emulated model name
8. Requests for the emulated model name will be routed to your real provider

### Stopping the Server

Use Pinokio's **"stop start.json"** button on the app's home page.

## Usage

### Model Name Emulation

The key feature of this emulator is **model name translation**:

```
Pinokio app requests: model="llama3"
                ↓
Emulator checks: emulatedModelName matches "llama3"? Yes
                ↓
Routes to: Anthropic Claude 3.5 Sonnet (your configured provider/model)
                ↓
Returns response: model="llama3" (Pinokio thinks it talked to llama3)
```

### Using the Endpoint

Point any OpenAI-compatible application to:
```
http://localhost:11434/v1/chat/completions
```

**Example: curl (requesting emulated model)**
```bash
# If emulatedModelName is set to "llama3"
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
# Actually routes to your configured provider (e.g., Anthropic Claude)
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

**Example: Another Pinokio App**

Configure the app with:
- **API Base URL**: `http://localhost:11434/v1`
- **API Key**: (any value or leave blank)
- **Model**: Your configured emulated model name (e.g., `llama3`)

### Health Check & Status

**Provider connectivity check:**
```bash
curl http://localhost:11434/health
```

**Emulator status (recommended):**
```bash
curl http://localhost:11434/emulator/status
```

Returns:
```json
{
  "emulatorRunning": true,
  "providerOnline": true,
  "providerConfigured": true,
  "currentConfig": {
    "provider": "anthropic",
    "providerName": "Anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "emulatedModelName": "llama3",
    "apiKeyEnvVar": "ANTHROPIC_API_KEY"
  }
}
```

## Supported Providers

| Provider | Models | Environment Variable |
|----------|--------|---------------------|
| OpenAI | GPT-4, GPT-4 Turbo, GPT-4o, o1 | `OPENAI_API_KEY` |
| Anthropic | Claude 3.5 Sonnet, Claude 3 Opus | `ANTHROPIC_API_KEY` |
| Groq | Llama 3.3 70B, Mixtral 8x7B | `GROQ_API_KEY` |
| Mistral | Mistral Large, Codestral | `MISTRAL_API_KEY` |
| Google | Gemini 1.5 Pro, Gemini 1.5 Flash | `GEMINI_API_KEY` |
| Cohere | Command R+, Command R | `COHERE_API_KEY` |
| Together AI | Llama 3.3 70B, Qwen 2.5 72B | `TOGETHER_API_KEY` |
| OpenRouter | Access to many providers | `OPENROUTER_API_KEY` |
| DeepSeek | DeepSeek Chat, DeepSeek Coder | `DEEPSEEK_API_KEY` |
| Cerebras | Llama 3.1 8B, Llama 3.1 70B | `CEREBRAS_API_KEY` |

**Note**: Providers are dynamically detected based on API key presence in the environment.

## Architecture

```
Request Flow:
┌─────────────────────┐
│ Pinokio App         │
│ requests "llama3"   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Virtual Model       │
│ Emulator            │
│ ┌─────────────────┐ │
│ │ Check if model  │ │
│ │ = emulatedName  │ │
│ └────────┬────────┘ │
│          ↓          │
│ ┌─────────────────┐ │
│ │ Route to real   │ │
│ │ provider/model  │ │
│ └────────┬────────┘ │
│          ↓          │
│ ┌─────────────────┐ │
│ │ Return response │ │
│ │ as "llama3"     │ │
│ └─────────────────┘ │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Pinokio App         │
│ receives response   │
│ from "llama3"       │
└─────────────────────┘
```

### File Structure

```
/virtual-model-emulator
├── server/
│   ├── main.py           # FastAPI server with account management endpoints
│   ├── config.py         # Configuration and account storage
│   ├── logger.py         # Logging and diagnostics
│   ├── litellm_client.py # Dynamic provider detection via LiteLLM
│   └── openai_adapter.py # Model name emulation routing
├── config/
│   ├── default.json      # User configuration (includes account, emulatedModelName)
│   ├── accounts.json     # Saved provider accounts (API keys)
│   ├── models-cache.json # Cached model list
│   └── saved-configs.json # Saved presets
├── public/
│   ├── config.html       # Emulator configuration UI (4-step hierarchy)
│   └── connect.html      # Provider account management UI
├── tests/
│   └── test_adapter.py   # pytest tests
├── pinokio.js            # Pinokio app definition (3 tabs)
├── install.json          # Dependency installation
├── start.json            # Server startup (daemon)
├── requirements.txt      # Python dependencies
└── .env.example          # API key template
```

## API Endpoints

### `POST /v1/chat/completions`

OpenAI-compatible chat completions with model name emulation.

**Request:**
```json
{
  "model": "llama3",
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama3",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hi!"},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

### `GET /health`

Provider connectivity check.

### `GET /emulator/status`

Comprehensive emulator status including:
- `emulatorRunning`: Whether the emulator is actively routing requests
- `providerOnline`: Whether the configured provider is reachable
- `currentConfig`: Current configuration including emulated model name

### `GET /providers`

List all providers with their connection status.

### `GET /providers/accounts`

List all saved accounts (API keys stored via Connect tab).

### `POST /providers/connect`

Save an API key for a provider.

**Request:**
```json
{
  "provider": "anthropic",
  "accountName": "Personal",
  "apiKey": "sk-ant-..."
}
```

### `POST /providers/disconnect`

Remove a saved account.

**Request:**
```json
{
  "provider": "anthropic",
  "accountName": "Personal"
}
```

### `GET /providers/models`

Get models for a specific provider (optionally filtered by account).

### `GET /models`

List available models, optionally filtered by provider.

### `GET /config/state`

Current configuration, presets, models, and emulator state.

### `POST /emulator/start`

Activate the emulator with specified provider, model, and emulated model name.

### `POST /emulator/stop`

Deactivate the emulator.

### `POST /config/savePreset`

Save a configuration preset including emulated model name.

## Limitations

1. **Text-Only**: Chat completions only - no images, audio, or file uploads
2. **No Streaming**: Responses returned complete, not streamed
3. **Estimated Tokens**: Token counts approximate (4 chars ~ 1 token)
4. **No Function Calling**: OpenAI tool/function calling not supported

## Troubleshooting

**Server won't start**
- Check if port 11434 is in use
- Change port in `config/default.json`
- Verify Python 3.10+ installed

**Provider not showing in dropdown**
- Check that the API key is set in `.env` file
- Restart the server after adding keys
- Check "Connected Providers" section for status

**Provider connection fails**
- Verify API key is set in `.env` file
- Check API key is valid with the provider
- Click "Test Connection" in UI for diagnostics

**"Model not found" error**
- Check that the requested model matches your configured `emulatedModelName`
- If `emulatedModelName` is set, only that exact name will work
- Leave `emulatedModelName` empty to accept any model name

**Models not loading**
- Check internet connection
- Verify provider API key is valid
- Click "Refresh" in UI

**Configuration UI won't open**
- Ensure server running (check Pinokio app home)
- Access directly: `http://localhost:11434/config.html`
- Check browser console for errors

## Development

**Running Tests:**
```bash
pytest tests/ -v
```

**Adding Providers:**
Edit `server/litellm_client.py` and add to `PROVIDER_REGISTRY`.

## Resources

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)
- [Pinokio Documentation](https://docs.pinokio.computer/)

## License

MIT

## Contributing

Feel free to fork and extend for your needs.
