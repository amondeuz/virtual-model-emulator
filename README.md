# Virtual Model Emulator v2.0.0-beta.6

A Pinokio app that provides a local OpenAI-compatible HTTP endpoint with **model name emulation** powered by LiteLLM proxy server. Route any model name to any provider - make Pinokio apps think they're talking to one model while actually using another.

## What is this?

A **model name emulator** that translates model names for Pinokio applications. Configure your preferred provider and model, set an emulated model name, and Pinokio apps will believe they're using that model while actually getting responses from your configured provider.

**Example**: Configure the emulator to respond to `llama3` requests while actually routing them to Anthropic Claude 3.5 Sonnet.

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

- **Direct LiteLLM Proxy**: No wrapper server - LiteLLM runs directly
- **Simple UI**: Single-page configuration at `http://localhost:8765/config.html`
- **Secure Key Handling**: API keys sent directly to LiteLLM, never stored in browser
- **4-Step Configuration**: Provider → Model → API Key → Emulated Name
- **OpenAI-Compatible Endpoint**: LiteLLM serves at `/v1/chat/completions`
- **100+ Providers**: Access OpenAI, Anthropic, Groq, Mistral, Google Gemini, and more

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

### Configuration UI

Access the configuration UI at:
```
http://localhost:8765/config.html
```

**4-Step Configuration:**
1. **Provider** - Select the AI provider (OpenAI, Anthropic, etc.)
2. **Model** - Enter the actual model ID from that provider
3. **API Key** - Paste your API key (sent to LiteLLM, not stored in browser)
4. **Emulated Model Name** - What Pinokio apps will request

### Workflow

1. **Open the UI** via Pinokio
2. **Select a Provider** from the dropdown
3. **Enter the model name** for that provider
4. **Paste your API key** (link provided to get key from provider)
5. **Choose an Emulated Model Name** (e.g., "llama3")
6. Click **Add Model**
7. Configure your Pinokio app to use the emulated model name

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

| Provider | Example Models |
|----------|----------------|
| OpenAI | gpt-4, gpt-4-turbo, gpt-4o, o1 |
| Anthropic | claude-3-5-sonnet, claude-3-opus |
| Groq | llama-3.3-70b, mixtral-8x7b |
| Mistral | mistral-large, codestral |
| Google | gemini-1.5-pro, gemini-2.0-flash |
| Cohere | command-r-plus, command-r |
| Together AI | llama-3.3-70b, qwen-2.5-72b |
| OpenRouter | any model via OpenRouter |
| DeepSeek | deepseek-chat, deepseek-coder |
| Cerebras | llama-3.1-8b, llama-3.1-70b |

## File Structure

```
/virtual-model-emulator
├── public/
│   └── config.html       # Configuration UI
├── server.py             # Static file server for UI
├── start.js              # Pinokio start script
├── install.js            # Pinokio install script
├── pinokio.js            # Pinokio app definition
├── config.yaml           # LiteLLM config (generated)
├── requirements.txt      # Python dependencies (litellm[proxy])
├── CHANGELOG.md          # Version history
└── README.md             # This file
```

## Security

- **API keys are NOT stored in the browser** - entered when adding models
- **Keys sent directly to LiteLLM** which stores them server-side
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
