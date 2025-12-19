# Virtual Model Emulator

A Pinokio app that provides a local OpenAI-compatible HTTP endpoint with **model name emulation** powered by LiteLLM. Route any model name to any provider - make Pinokio apps think they're talking to one model while actually using another.

## What is this?

A **model name emulator** that translates model names for Pinokio applications. Configure your preferred provider and model, set an emulated model name, and Pinokio apps will believe they're using that model while actually getting responses from your configured provider.

**Example**: Configure the emulator to respond to `llama3` requests while actually routing them to Anthropic Claude 3.5 Sonnet.

### Key Features

- **Model Name Emulation**: Apps request "llama3" but get Claude, GPT-4, or any other model
- **Dynamic Provider Detection**: Only shows providers with API keys configured
- **OpenAI-Compatible Endpoint**: POST to `/v1/chat/completions` just like OpenAI
- **100+ Providers**: Access OpenAI, Anthropic, Groq, Mistral, Google Gemini, Cohere, Together AI, and more
- **Connect Tab**: Visual overview of all providers and their connection status
- **Searchable Dropdowns**: Quick search-as-you-type for providers and models
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

### API Keys

Create a `.env` file in the project root with your API keys:

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

**Note**: Only providers with API keys configured will be shown in the UI.

### Configuration UI

The configuration UI opens automatically when the app starts, or access it at:
```
http://localhost:11434/config.html
```

**Features:**
- **Connected Providers**: Collapsible section showing all providers and their connection status
- **Real Provider**: Select from connected providers (only those with API keys)
- **Real Model**: Search/select from available models for the selected provider
- **Emulated Model Name**: The model name that Pinokio apps will request
- **API Key Env Var**: Configure which environment variable contains your API key
- **Presets**: Save configurations for quick switching between setups
- **Test Connection**: Verify your API key works before starting
- **Status Indicators**: Separate indicators for provider connectivity and emulator state

### Workflow

1. Check the "Connected Providers" section to see which providers have API keys
2. Select a provider from the dropdown (only connected providers shown)
3. Select a model for that provider
4. **Important**: Enter an "Emulated Model Name" (e.g., `llama3`, `gpt-4`)
5. Click "Test Connection" to verify the provider works
6. Click "Start" to activate the emulator
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
/model-emulator
├── server/
│   ├── main.py           # FastAPI server with /emulator/status endpoint
│   ├── config.py         # Configuration with emulatedModelName field
│   ├── logger.py         # Logging and diagnostics
│   ├── litellm_client.py # Dynamic provider detection via LiteLLM
│   └── openai_adapter.py # Model name emulation routing
├── config/
│   ├── default.json      # User configuration (includes emulatedModelName)
│   ├── models-cache.json # Cached model list
│   └── saved-configs.json # Saved presets
├── public/
│   └── config.html       # Configuration UI with Connect tab
├── tests/
│   └── test_adapter.py   # pytest tests
├── pinokio.js            # Pinokio app definition
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
