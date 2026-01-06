"""
Backend server for Virtual Model Emulator.
Uses LiteLLM SDK directly (no proxy needed).
"""
import json
import os
import http.server
import socketserver
import threading
import time
from pathlib import Path

# Import LiteLLM SDK
try:
    import litellm
    litellm.drop_params = True
    litellm.set_verbose = False
except ImportError:
    print("[ERROR] LiteLLM not installed. Run: pip install litellm", flush=True)
    litellm = None

BASE_DIR = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"
CONFIG_DIR = BASE_DIR / "config"
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"
EMULATIONS_FILE = CONFIG_DIR / "emulations.json"

# Thread-safe lock for emulation operations
_emulation_lock = threading.Lock()

# In-memory emulation state (persisted to JSON)
_active_emulations = []

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)


def load_accounts():
    """Load accounts from JSON file."""
    if ACCOUNTS_FILE.exists():
        try:
            return json.loads(ACCOUNTS_FILE.read_text())
        except Exception:
            pass
    return []


def save_accounts(accounts):
    """Save accounts to JSON file."""
    ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2))


def load_emulations():
    """Load emulations from JSON file."""
    global _active_emulations
    if EMULATIONS_FILE.exists():
        try:
            _active_emulations = json.loads(EMULATIONS_FILE.read_text())
            return _active_emulations
        except Exception:
            pass
    _active_emulations = []
    return []


def save_emulations():
    """Save emulations to JSON file."""
    global _active_emulations
    EMULATIONS_FILE.write_text(json.dumps(_active_emulations, indent=2))


def get_accounts_for_provider(provider_id):
    """Get all accounts for a specific provider."""
    accounts = load_accounts()
    return [a for a in accounts if a["provider"] == provider_id]


def get_providers_with_accounts():
    """Get list of provider IDs that have at least one account."""
    accounts = load_accounts()
    return list(set(acc["provider"] for acc in accounts))


def get_provider_by_id(provider_id):
    """Get provider info by ID."""
    if not provider_id or not isinstance(provider_id, str):
        return None
    return next((p for p in PROVIDERS if p["id"] == provider_id), None)


def find_api_key_for_provider(provider_id, account_name=None):
    """Find API key for a provider from accounts or environment variables."""
    if not provider_id:
        return None

    # Check saved accounts first
    accounts = load_accounts()
    for acc in accounts:
        if acc.get("provider") == provider_id:
            if not account_name or acc.get("accountName") == account_name:
                return acc.get("apiKey")

    # Fall back to environment variable
    prov = get_provider_by_id(provider_id)
    if prov:
        return os.environ.get(prov["envVar"])

    return None


def has_any_api_keys():
    """Check if ANY provider has an API key configured."""
    accounts = load_accounts()
    if len(accounts) > 0:
        return True
    return any(os.environ.get(p["envVar"]) for p in PROVIDERS)


def _sanitize_error(error_msg):
    """Remove potentially sensitive information from error messages."""
    if not error_msg:
        return "Unknown error"

    sensitive_patterns = ['api_key', 'apikey', 'api-key', 'bearer', 'token', 'password', 'secret']
    error_lower = str(error_msg).lower()

    for pattern in sensitive_patterns:
        if pattern in error_lower:
            return "Request failed (details logged server-side)"

    return str(error_msg)


# Providers sorted alphabetically by name (LiteLLM SDK format)
PROVIDERS = [
    {"id": "aiml", "name": "AI/ML API", "envVar": "AIML_API_KEY", "prefix": "aiml_api/"},
    {"id": "anthropic", "name": "Anthropic", "envVar": "ANTHROPIC_API_KEY", "prefix": "anthropic/"},
    {"id": "cerebras", "name": "Cerebras", "envVar": "CEREBRAS_API_KEY", "prefix": "cerebras/"},
    {"id": "deepseek", "name": "DeepSeek", "envVar": "DEEPSEEK_API_KEY", "prefix": "deepseek/"},
    {"id": "gemini", "name": "Google Gemini", "envVar": "GEMINI_API_KEY", "prefix": "gemini/"},
    {"id": "groq", "name": "Groq", "envVar": "GROQ_API_KEY", "prefix": "groq/"},
    {"id": "huggingface", "name": "Hugging Face", "envVar": "HF_TOKEN", "prefix": "huggingface/"},
    {"id": "mistral", "name": "Mistral", "envVar": "MISTRAL_API_KEY", "prefix": "mistral/"},
    {"id": "openai", "name": "OpenAI", "envVar": "OPENAI_API_KEY", "prefix": ""},
    {"id": "openrouter", "name": "OpenRouter", "envVar": "OPENROUTER_API_KEY", "prefix": "openrouter/"},
    {"id": "together", "name": "Together AI", "envVar": "TOGETHER_API_KEY", "prefix": "together_ai/"},
]

# Static model lists per provider (commonly available models)
PROVIDER_MODELS = {
    "aiml": [
        "gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini",
        "claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku",
        "Llama-3.2-3B-Instruct-Turbo", "Llama-3.2-11B-Vision-Instruct-Turbo",
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
    ],
    "cerebras": [
        "llama3.1-8b", "llama3.1-70b",
    ],
    "deepseek": [
        "deepseek-chat", "deepseek-reasoner",
    ],
    "gemini": [
        "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b",
    ],
    "groq": [
        "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant",
        "llama3-70b-8192", "llama3-8b-8192",
        "mixtral-8x7b-32768", "gemma2-9b-it",
    ],
    "huggingface": [
        "meta-llama/Llama-3.2-3B-Instruct", "meta-llama/Llama-3.2-1B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
    ],
    "mistral": [
        "mistral-large-latest", "mistral-medium-latest", "mistral-small-latest",
        "open-mistral-7b", "open-mixtral-8x7b", "open-mixtral-8x22b",
    ],
    "openai": [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
        "gpt-3.5-turbo", "o1-preview", "o1-mini",
    ],
    "openrouter": [
        "openai/gpt-4o", "openai/gpt-4o-mini",
        "anthropic/claude-3.5-sonnet", "anthropic/claude-3-opus",
        "meta-llama/llama-3.1-405b-instruct", "meta-llama/llama-3.1-70b-instruct",
        "google/gemini-pro-1.5", "mistralai/mistral-large",
    ],
    "together": [
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "mistralai/Mixtral-8x22B-Instruct-v0.1",
        "Qwen/Qwen2.5-72B-Instruct-Turbo",
    ],
}


class APIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def read_json_body(self):
        """Read and parse JSON body from request."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length:
                raw_body = self.rfile.read(content_length)
                return json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[WARN] Failed to parse JSON body: {e}", flush=True)
        except Exception as e:
            print(f"[WARN] Unexpected error reading request body: {e}", flush=True)
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/providers/accounts":
            accounts = load_accounts()
            safe_accounts = [{"provider": a["provider"], "accountName": a["accountName"]} for a in accounts]
            self.send_json(safe_accounts)

        elif path == "/config/state":
            accounts = load_accounts()
            safe_accounts = [{"provider": a["provider"], "accountName": a["accountName"]} for a in accounts]

            # Get providers with connection status
            providers_with_status = []
            for p in PROVIDERS:
                has_account = any(a["provider"] == p["id"] for a in accounts)
                has_env = os.environ.get(p["envVar"]) is not None
                providers_with_status.append({
                    **p,
                    "hasApiKey": has_account or has_env
                })

            # Get active emulations
            global _active_emulations
            emulator_active = len(_active_emulations) > 0
            any_provider_available = has_any_api_keys()

            self.send_json({
                "accounts": safe_accounts,
                "providers": providers_with_status,
                "models": [],
                "presets": [],
                "config": {},
                "emulatorActive": emulator_active,
                "providerOnline": any_provider_available
            })

        elif path == "/emulator/status":
            global _active_emulations
            any_provider_available = has_any_api_keys()

            self.send_json({
                "emulatorRunning": len(_active_emulations) > 0,
                "providerOnline": any_provider_available,
                "currentConfig": {
                    "emulatedModelName": _active_emulations[0]["emulatedName"] if _active_emulations else "",
                    "providerName": _active_emulations[0].get("provider", "") if _active_emulations else ""
                } if _active_emulations else None
            })

        elif path == "/health":
            # Always healthy since we're using SDK directly
            self.send_json({"online": True, "message": "API server running (LiteLLM SDK mode)"})

        elif path == "/emulator/active":
            global _active_emulations
            self.send_json({"active": _active_emulations, "count": len(_active_emulations)})

        elif path == "/providers/list":
            self.send_json({"providers": PROVIDERS})

        elif path == "/models":
            provider = query.get("provider", [""])[0]
            models = []

            if provider and provider in PROVIDER_MODELS:
                provider_info = get_provider_by_id(provider)
                for model_id in PROVIDER_MODELS.get(provider, []):
                    models.append({
                        "id": model_id,
                        "label": model_id,
                        "provider": provider,
                        "providerName": provider_info["name"] if provider_info else provider
                    })

            models.sort(key=lambda m: m.get("label", "").lower())
            self.send_json({"models": models})

        elif path == "/" or path == "":
            self.path = "/config.html"
            super().do_GET()

        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
        import urllib.parse
        import uuid
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/providers/connect":
            data = self.read_json_body()
            provider = data.get("provider")
            account_name = data.get("accountName")
            api_key = data.get("apiKey")

            if not all([provider, account_name, api_key]):
                self.send_json({"success": False, "error": "Missing required fields"}, 400)
                return

            accounts = load_accounts()

            # Check for duplicate
            for acc in accounts:
                if acc["provider"] == provider and acc["accountName"] == account_name:
                    self.send_json({"success": False, "error": "Account already exists"}, 400)
                    return

            # Save account
            new_account = {
                "provider": provider,
                "accountName": account_name,
                "apiKey": api_key
            }
            accounts.append(new_account)
            save_accounts(accounts)
            print(f"[OK] Connected provider: {provider}/{account_name}", flush=True)
            self.send_json({"success": True})

        elif path == "/providers/disconnect":
            data = self.read_json_body()
            provider = data.get("provider")
            account_name = data.get("accountName")

            accounts = load_accounts()
            accounts = [a for a in accounts if not (a["provider"] == provider and a["accountName"] == account_name)]
            save_accounts(accounts)
            print(f"[OK] Disconnected provider: {provider}/{account_name}", flush=True)
            self.send_json({"success": True})

        elif path == "/emulator/start":
            """Start model emulation."""
            data = self.read_json_body()
            account_name = data.get("account", "").strip()
            provider = data.get("provider", "").strip()
            model = data.get("model", "").strip()
            emulated_name = data.get("emulatedModelName", model).strip()

            if not provider or not model:
                self.send_json({"success": False, "error": "Provider and model required"}, 400)
                return

            if not emulated_name:
                self.send_json({"success": False, "error": "Emulated model name required"}, 400)
                return

            # Find API key
            api_key = find_api_key_for_provider(provider, account_name)
            if not api_key:
                self.send_json({"success": False, "error": "No API key found for provider"}, 400)
                return

            # Get provider prefix for LiteLLM SDK
            prov = get_provider_by_id(provider)
            prefix = prov["prefix"] if prov else ""
            full_model = f"{prefix}{model}"

            # Create emulation entry
            emulation_id = str(uuid.uuid4())
            emulation = {
                "id": emulation_id,
                "emulatedName": emulated_name,
                "actualModel": full_model,
                "provider": provider,
                "apiKey": api_key  # Stored securely for SDK calls
            }

            with _emulation_lock:
                global _active_emulations
                # Remove existing emulation with same name (if any)
                _active_emulations = [e for e in _active_emulations if e["emulatedName"] != emulated_name]
                _active_emulations.append(emulation)
                save_emulations()

            print(f"[OK] Started emulation: {emulated_name} → {full_model}", flush=True)
            self.send_json({
                "success": True,
                "modelId": emulation_id,
                "emulatedName": emulated_name,
                "actualModel": full_model
            })

        elif path == "/emulator/stop":
            """Stop all active emulations."""
            with _emulation_lock:
                global _active_emulations
                count = len(_active_emulations)
                stopped = [{"emulatedName": e["emulatedName"], "actualModel": e["actualModel"]} for e in _active_emulations]
                _active_emulations = []
                save_emulations()

            print(f"[OK] Stopped {count} emulation(s)", flush=True)
            self.send_json({
                "success": True,
                "deleted": count,
                "emulations": stopped
            })

        elif path == "/v1/chat/completions":
            """Handle chat completion using LiteLLM SDK."""
            if litellm is None:
                self.send_json({"error": "LiteLLM SDK not available"}, 500)
                return

            data = self.read_json_body()
            requested_model = data.get("model", "")
            messages = data.get("messages", [])

            if not messages:
                self.send_json({"error": "Messages required"}, 400)
                return

            # Find emulation for requested model
            emulation = None
            api_key = None
            actual_model = requested_model

            with _emulation_lock:
                global _active_emulations
                for em in _active_emulations:
                    if em["emulatedName"] == requested_model:
                        emulation = em
                        actual_model = em["actualModel"]
                        api_key = em["apiKey"]
                        break

            # If no emulation found, try to use the model directly
            if not emulation:
                # Try to find API key from provider prefix
                for prov in PROVIDERS:
                    if requested_model.startswith(prov["prefix"]) or prov["prefix"] == "":
                        api_key = find_api_key_for_provider(prov["id"])
                        if api_key:
                            break

            if not api_key:
                self.send_json({
                    "error": f"No emulation or API key configured for model: {requested_model}"
                }, 400)
                return

            try:
                # Use LiteLLM SDK directly
                response = litellm.completion(
                    model=actual_model,
                    messages=messages,
                    api_key=api_key,
                    temperature=data.get("temperature", 0.7),
                    max_tokens=data.get("max_tokens"),
                    stream=False
                )

                # Return OpenAI-compatible response with emulated model name
                result = {
                    "id": response.id,
                    "object": "chat.completion",
                    "created": response.created,
                    "model": requested_model,  # Return the requested (emulated) model name
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response.choices[0].message.content
                            },
                            "finish_reason": response.choices[0].finish_reason
                        }
                    ],
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    }
                }

                self.send_json(result)

            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Completion failed: {error_msg}", flush=True)
                self.send_json({
                    "error": {
                        "message": _sanitize_error(error_msg),
                        "type": "api_error",
                        "code": "completion_error"
                    }
                }, 500)

        else:
            self.send_json({"error": "Not found"}, 404)


def main():
    """Start API server with LiteLLM SDK integration."""
    import signal
    import errno
    import sys

    # Load emulations from file
    load_emulations()

    # Ensure required directories exist
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Get port from environment
    port = int(os.environ.get('API_SERVER_PORT', 8775))

    # Signal handling
    def signal_handler(sig, frame):
        print(f'[INFO] Received signal {sig}, shutting down...', flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start HTTP server
    try:
        with socketserver.TCPServer(("127.0.0.1", port), APIHandler) as httpd:
            # Output URL (required for app_launcher.py ready detection)
            print(f"http://localhost:{port}/config.html", flush=True)
            print(f"[INFO] API server started on port {port} (LiteLLM SDK mode)", flush=True)
            print(f"[OK] Server ready - No proxy needed!", flush=True)
            httpd.serve_forever()

    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"[ERROR] Port {port} is already in use", flush=True)
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
