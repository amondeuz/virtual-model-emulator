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
import subprocess
import platform
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
    """Load accounts from JSON file (always reads fresh from disk)."""
    if ACCOUNTS_FILE.exists():
        try:
            return json.loads(ACCOUNTS_FILE.read_text())
        except:
            pass
    return []

def save_accounts(accounts):
    """Save accounts to JSON file."""
    ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2))

def get_accounts_for_provider(provider_id):
    """Get all accounts for a specific provider."""
    accounts = load_accounts()
    return [a for a in accounts if a["provider"] == provider_id]

def get_providers_with_accounts():
    """Get list of provider IDs that have at least one account."""
    accounts = load_accounts()
    providers_with_accounts = set()
    for acc in accounts:
        providers_with_accounts.add(acc["provider"])
    return list(providers_with_accounts)

def regenerate_config_yaml():
    """Regenerate config.yaml with wildcards for providers that have accounts."""
    config_file = BASE_DIR / "config.yaml"
    master_key = get_master_key()
    
    providers_with_accounts = get_providers_with_accounts()
    
    # Get first API key for each provider (for wildcard route)
    accounts = load_accounts()
    provider_keys = {}
    for provider_id in providers_with_accounts:
        # Find first account for this provider
        for acc in accounts:
            if acc["provider"] == provider_id:
                provider_keys[provider_id] = acc["apiKey"]
                break
    
    # Build model_list with wildcards
    model_list = []
    for provider_id in sorted(providers_with_accounts):
        if provider_id in provider_keys:
            model_list.append({
                "model_name": f"{provider_id}/*",
                "litellm_params": {
                    "model": f"{provider_id}/*",
                    "api_key": provider_keys[provider_id]
                }
            })
    
    # Generate YAML content
    config_content = "model_list:\n"
    if model_list:
        for model in model_list:
            config_content += f"  - model_name: \"{model['model_name']}\"\n"
            config_content += f"    litellm_params:\n"
            config_content += f"      model: \"{model['litellm_params']['model']}\"\n"
            config_content += f"      api_key: \"{model['litellm_params']['api_key']}\"\n"
    else:
        config_content += "  []\n"
    
    config_content += f"\ngeneral_settings:\n"
    config_content += f"  master_key: {master_key}\n"
    config_content += f"\nlitellm_settings:\n"
    config_content += f"  drop_params: true\n"
    config_content += f"  check_provider_endpoint: true\n"
    
    config_file.write_text(config_content)
    print(f"[INFO] Regenerated config.yaml with {len(model_list)} wildcard providers")

def restart_litellm():
    """Restart LiteLLM process by killing it (Pinokio will auto-restart)."""
    try:
        if platform.system() == "Windows":
            # Kill litellm processes on Windows
            subprocess.run(["taskkill", "/F", "/IM", "litellm.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq litellm*"], capture_output=True)
        else:
            # Kill litellm processes on Unix
            subprocess.run(["pkill", "-f", "litellm"], capture_output=True)
        print("[INFO] Sent restart signal to LiteLLM")
        return True
    except Exception as e:
        print(f"[WARNING] Could not restart LiteLLM: {e}")
        return False

def is_wildcard_model(model_name):
    """Check if a model is a wildcard passthrough (not an explicit emulation)."""
    return model_name and '*' in model_name

def get_active_emulations(model_info):
    """Get only explicitly configured emulations (not wildcards)."""
    if "data" not in model_info:
        return []
    return [m for m in model_info["data"] if not is_wildcard_model(m.get("model_name", ""))]

def has_any_api_keys():
    """Check if ANY provider has an API key configured (accounts or env vars)."""
    accounts = load_accounts()
    if len(accounts) > 0:
        return True
    return any(os.environ.get(p["envVar"]) for p in PROVIDERS)

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
            litellm_alive = "error" not in health

            model_info = litellm_request("/model/info")
            active_emulations = get_active_emulations(model_info)
            emulator_active = len(active_emulations) > 0

            # Provider is only "online" if LiteLLM is running AND we have API keys
            provider_online = litellm_alive and has_any_api_keys()

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
            litellm_alive = "error" not in health

            model_info = litellm_request("/model/info")
            active_emulations = get_active_emulations(model_info)

            # Provider is only "online" if LiteLLM is running AND we have API keys
            provider_online = litellm_alive and has_any_api_keys()

            self.send_json({
                "emulatorRunning": len(active_emulations) > 0,
                "providerOnline": provider_online,
                "currentConfig": {
                    "emulatedModelName": active_emulations[0]["model_name"] if active_emulations else "",
                    "providerName": ""
                } if active_emulations else None
            })

        elif path == "/health":
            health = litellm_request("/health")
            online = "error" not in health
            self.send_json({"online": online, "message": "LiteLLM is running" if online else "LiteLLM offline"})

        elif path == "/emulator/active":
            # Return currently active/emulated models from LiteLLM (excluding wildcards)
            model_info = litellm_request("/model/info")
            active_emulations = get_active_emulations(model_info)
            active_models = []
            for m in active_emulations:
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

            # Sort models alphabetically by label
            models.sort(key=lambda m: m.get("label", "").lower())
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

            # Check if this is the first account for this provider
            provider_accounts = get_accounts_for_provider(provider)
            is_first_account = len(provider_accounts) == 0

            accounts.append({
                "provider": provider,
                "accountName": account_name,
                "apiKey": api_key
            })
            save_accounts(accounts)

            # Regenerate config.yaml and restart LiteLLM if this is the first account for this provider
            if is_first_account:
                regenerate_config_yaml()
                restart_litellm()

            self.send_json({"success": True})

        elif path == "/providers/disconnect":
            data = self.read_json_body()
            provider = data.get("provider")
            account_name = data.get("accountName")

            accounts = load_accounts()
            accounts = [a for a in accounts if not (a["provider"] == provider and a["accountName"] == account_name)]
            save_accounts(accounts)

            # Check if any accounts remain for this provider
            remaining_accounts = get_accounts_for_provider(provider)
            if len(remaining_accounts) == 0:
                # Remove wildcard from config.yaml and restart LiteLLM
                regenerate_config_yaml()
                restart_litellm()

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

            # For now, emulations are added via config.yaml
            # This endpoint acknowledges the request but actual implementation
            # would require writing to config.yaml and restarting LiteLLM
            self.send_json({"success": True, "message": "Emulation feature requires config.yaml update"})

        elif path == "/emulator/stop":
            # For config.yaml approach, stopping means removing explicit emulations
            # Wildcards remain in place
            self.send_json({"success": True, "deleted": 0})

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
