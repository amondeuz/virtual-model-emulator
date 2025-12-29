"""
Backend server for Virtual Model Emulator.
Provides API endpoints for the UI and proxies to LiteLLM.
"""
import json
import os
import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

PORT = 8765
LITELLM_URL = "http://127.0.0.1:11434"
BASE_DIR = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"
CONFIG_DIR = BASE_DIR / "config"
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)

def get_master_key():
    """Read master key from config.yaml."""
    config_file = BASE_DIR / "config.yaml"
    if config_file.exists():
        content = config_file.read_text()
        for line in content.split('\n'):
            if 'master_key:' in line:
                return line.split('master_key:')[1].strip()
    return "sk-litellm-master-key"

def load_accounts():
    """Load accounts from JSON file."""
    if ACCOUNTS_FILE.exists():
        try:
            return json.loads(ACCOUNTS_FILE.read_text())
        except:
            pass
    return []

def save_accounts(accounts):
    """Save accounts to JSON file."""
    ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2))

def litellm_request(path, method="GET", data=None):
    """Make request to LiteLLM API."""
    url = f"{LITELLM_URL}{path}"
    headers = {
        "Authorization": f"Bearer {get_master_key()}",
        "Content-Type": "application/json"
    }

    try:
        if data:
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "status": e.code}
    except Exception as e:
        return {"error": str(e)}

# Providers sorted alphabetically by name
PROVIDERS = [
    {"id": "aiml", "name": "AI/ML API", "envVar": "AIML_API_KEY", "prefix": "aiml/"},
    {"id": "bytez", "name": "Bytez", "envVar": "BYTEZ_API_KEY", "prefix": "bytez/"},
    {"id": "cerebras", "name": "Cerebras", "envVar": "CEREBRAS_API_KEY", "prefix": "cerebras/"},
    {"id": "cloudflare", "name": "Cloudflare Workers AI", "envVar": "CLOUDFLARE_API_KEY", "prefix": "cloudflare/"},
    {"id": "deepseek", "name": "DeepSeek", "envVar": "DEEPSEEK_API_KEY", "prefix": "deepseek/"},
    {"id": "gemini", "name": "Google Gemini", "envVar": "GEMINI_API_KEY", "prefix": "gemini/"},
    {"id": "groq", "name": "Groq", "envVar": "GROQ_API_KEY", "prefix": "groq/"},
    {"id": "huggingface", "name": "Hugging Face", "envVar": "HF_TOKEN", "prefix": "huggingface/"},
    {"id": "openrouter", "name": "OpenRouter", "envVar": "OPENROUTER_API_KEY", "prefix": "openrouter/"},
]

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
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length:
            return json.loads(self.rfile.read(content_length).decode())
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API endpoints
        if path == "/providers/accounts":
            accounts = load_accounts()
            # Return accounts without exposing API keys
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

            # Models are loaded dynamically when provider is selected via /models endpoint
            models = []

            # Check if emulator is running
            health = litellm_request("/health")
            provider_online = "error" not in health

            model_info = litellm_request("/model/info")
            emulator_active = provider_online and "data" in model_info and len(model_info["data"]) > 0

            self.send_json({
                "accounts": safe_accounts,
                "providers": providers_with_status,
                "models": models,
                "presets": [],
                "config": {},
                "emulatorActive": emulator_active,
                "providerOnline": provider_online
            })

        elif path == "/emulator/status":
            health = litellm_request("/health")
            online = "error" not in health

            model_info = litellm_request("/model/info")
            models = model_info.get("data", [])

            self.send_json({
                "emulatorRunning": online and len(models) > 0,
                "providerOnline": online,
                "currentConfig": {
                    "emulatedModelName": models[0]["model_name"] if models else "",
                    "providerName": ""
                } if models else None
            })

        elif path == "/health":
            health = litellm_request("/health")
            online = "error" not in health
            self.send_json({"online": online, "message": "LiteLLM is running" if online else "LiteLLM offline"})

        elif path == "/emulator/active":
            # Return currently active/emulated models from LiteLLM
            model_info = litellm_request("/model/info")
            active_models = []
            if "data" in model_info:
                for m in model_info["data"]:
                    model_name = m.get("model_name", "")
                    litellm_model = m.get("litellm_params", {}).get("model", "")
                    active_models.append({
                        "emulatedName": model_name,
                        "actualModel": litellm_model,
                        "id": m.get("model_info", {}).get("id", model_name)
                    })
            self.send_json({"active": active_models, "count": len(active_models)})

        elif path == "/models":
            provider = query.get("provider", [""])[0]
            models = []

            # Query LiteLLM proxy for available models
            result = litellm_request("/v1/models")
            if "data" in result:
                provider_info = next((p for p in PROVIDERS if p["id"] == provider), None) if provider else None
                prefix = provider_info["prefix"] if provider_info else ""

                for m in result["data"]:
                    model_id = m.get("id", "")
                    # Filter by provider if specified
                    if provider:
                        if prefix and model_id.startswith(prefix):
                            models.append({
                                "id": model_id[len(prefix):],
                                "label": model_id[len(prefix):],
                                "provider": provider,
                                "providerName": provider_info["name"] if provider_info else provider
                            })
                        elif not prefix and "/" not in model_id:
                            models.append({
                                "id": model_id,
                                "label": model_id,
                                "provider": provider,
                                "providerName": provider_info["name"] if provider_info else provider
                            })
                    else:
                        models.append({
                            "id": model_id,
                            "label": model_id,
                            "provider": "",
                            "providerName": ""
                        })

            self.send_json({"models": models})

        elif path == "/" or path == "":
            self.path = "/config.html"
            super().do_GET()

        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
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

            accounts.append({
                "provider": provider,
                "accountName": account_name,
                "apiKey": api_key
            })
            save_accounts(accounts)
            self.send_json({"success": True})

        elif path == "/providers/disconnect":
            data = self.read_json_body()
            provider = data.get("provider")
            account_name = data.get("accountName")

            accounts = load_accounts()
            accounts = [a for a in accounts if not (a["provider"] == provider and a["accountName"] == account_name)]
            save_accounts(accounts)
            self.send_json({"success": True})

        elif path == "/emulator/start":
            data = self.read_json_body()
            account_name = data.get("account", "")
            provider = data.get("provider")
            model = data.get("model")
            emulated_name = data.get("emulatedModelName", model)

            if not provider or not model:
                self.send_json({"success": False, "error": "Provider and model required"}, 400)
                return

            # Find API key
            accounts = load_accounts()
            api_key = None
            for acc in accounts:
                if acc["provider"] == provider:
                    if not account_name or acc["accountName"] == account_name:
                        api_key = acc["apiKey"]
                        break

            # Fall back to env var
            if not api_key:
                prov = next((p for p in PROVIDERS if p["id"] == provider), None)
                if prov:
                    api_key = os.environ.get(prov["envVar"])

            if not api_key:
                self.send_json({"success": False, "error": "No API key found for provider"}, 400)
                return

            # Get provider prefix
            prov = next((p for p in PROVIDERS if p["id"] == provider), None)
            prefix = prov["prefix"] if prov else ""
            full_model = f"{prefix}{model}"

            # Add model to LiteLLM
            result = litellm_request("/model/new", "POST", {
                "model_name": emulated_name,
                "litellm_params": {
                    "model": full_model,
                    "api_key": api_key
                }
            })

            if "error" in result:
                self.send_json({"success": False, "error": result["error"]}, 500)
            else:
                self.send_json({"success": True})

        elif path == "/emulator/stop":
            # Get current models and delete them
            model_info = litellm_request("/model/info")
            if "data" in model_info:
                for m in model_info["data"]:
                    # Use model_info.id for deletion, fallback to model_name
                    model_id = m.get("model_info", {}).get("id") or m.get("model_name")
                    if model_id:
                        litellm_request("/model/delete", "POST", {"id": model_id})
            self.send_json({"success": True})

        elif path == "/config/save":
            # Just acknowledge - config is applied on start
            self.send_json({"success": True})

        elif path == "/config/savePreset":
            # Presets not implemented yet
            self.send_json({"success": False, "error": "Presets not implemented"}, 501)

        else:
            self.send_json({"error": "Not found"}, 404)

def main():
    with socketserver.TCPServer(("127.0.0.1", PORT), APIHandler) as httpd:
        print(f"http://localhost:{PORT}/config.html")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
