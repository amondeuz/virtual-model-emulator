"""
Backend server for Virtual Model Emulator.
Provides API endpoints for the UI and proxies to LiteLLM.
"""
import json
import os
import http.server
import socketserver
import threading
import urllib.request
import urllib.parse
import urllib.error
import uuid
from pathlib import Path

PORT = 8765
LITELLM_URL = "http://127.0.0.1:11434"
BASE_DIR = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"
CONFIG_DIR = BASE_DIR / "config"
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"

# Lock for thread-safe wildcard operations (prevents race conditions with rapid clicks)
_wildcard_lock = threading.Lock()

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)

def get_master_key():
    """Read and validate master key from config.yaml.

    LiteLLM requires master key to start with 'sk-' and be at least 32 chars.
    """
    config_file = BASE_DIR / "config.yaml"
    master_key = "sk-litellm-master-key"

    if config_file.exists():
        content = config_file.read_text()
        for line in content.split('\n'):
            if 'master_key:' in line:
                master_key = line.split('master_key:')[1].strip()
                break

    # Validate master key format
    if not master_key.startswith('sk-'):
        print(f"[WARNING] Master key must start with 'sk-'. Current key: {master_key[:10]}...", flush=True)
        print("[WARNING] LiteLLM may reject this key. Edit config.yaml to fix.", flush=True)

    if len(master_key) < 32:
        print(f"[WARNING] Master key should be at least 32 characters. Current length: {len(master_key)}", flush=True)

    return master_key

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

def add_wildcard_to_database(provider_id, api_key):
    """Add a wildcard route for a provider to the LiteLLM database via /model/new API.

    Thread-safe: Uses lock to prevent race conditions from rapid clicks.
    """
    with _wildcard_lock:
        # Check if wildcard already exists (defensive - prevents duplicates)
        models_info = litellm_request("/model/info")
        if "data" in models_info:
            for model_data in models_info.get("data", []):
                model_name = model_data.get("model_info", {}).get("model_name", "")
                if model_name == f"{provider_id}/*":
                    print(f"[INFO] Wildcard route {provider_id}/* already exists in database", flush=True)
                    return {"success": True, "message": "Already exists"}

        model_data = {
            "model_name": f"{provider_id}/*",
            "litellm_params": {
                "model": f"{provider_id}/*",
                "api_key": api_key
            }
        }
        result = litellm_request("/model/new", method="POST", data=model_data)
        if "error" not in result:
            print(f"[INFO] Added wildcard route {provider_id}/* to database", flush=True)
        else:
            print(f"[WARNING] Failed to add wildcard route {provider_id}/*: {result.get('error')}", flush=True)
        return result

def remove_wildcard_from_database(provider_id):
    """Remove a wildcard route for a provider from the LiteLLM database via /model/delete API."""
    # Get current models from database
    models_info = litellm_request("/model/info")

    if "error" in models_info:
        print(f"[WARNING] Failed to get model info: {models_info.get('error')}", flush=True)
        return False

    # Find and delete the wildcard route for this provider
    for model_data in models_info.get("data", []):
        model_info = model_data.get("model_info", {})
        model_name = model_info.get("model_name", "")

        if model_name == f"{provider_id}/*":
            model_id = model_info.get("id")
            if model_id:
                result = litellm_request("/model/delete", method="POST", data={"id": model_id})
                if "error" not in result:
                    print(f"[INFO] Removed wildcard route {provider_id}/* from database", flush=True)
                    return True
                else:
                    print(f"[WARNING] Failed to remove wildcard route: {result.get('error')}", flush=True)
    return False

def is_wildcard_model(model_name):
    """Check if a model is a wildcard passthrough (not an explicit emulation)."""
    return model_name and '*' in model_name

def get_active_emulations(model_info):
    """Get only explicitly configured emulations (not wildcards)."""
    if "data" not in model_info:
        return []
    return [m for m in model_info["data"] if not is_wildcard_model(m.get("model_name", ""))]

def get_provider_by_id(provider_id):
    """Get provider info by ID.

    Args:
        provider_id: The provider ID (e.g., 'groq', 'gemini')

    Returns:
        dict: Provider info dict or None if not found
    """
    if not provider_id or not isinstance(provider_id, str):
        return None
    return next((p for p in PROVIDERS if p["id"] == provider_id), None)


def find_api_key_for_provider(provider_id, account_name=None):
    """Find API key for a provider from accounts or environment variables.

    Args:
        provider_id: The provider ID
        account_name: Optional specific account name to use

    Returns:
        str: API key or None if not found
    """
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
    """Check if ANY provider has an API key configured (accounts or env vars).

    Note: This checks system-wide availability, not a specific provider.
    Use get_accounts_for_provider() to check a specific provider.
    """
    accounts = load_accounts()
    if len(accounts) > 0:
        return True
    return any(os.environ.get(p["envVar"]) for p in PROVIDERS)

def _sanitize_error(error_msg):
    """Remove potentially sensitive information from error messages.

    Strips API keys and other credentials that might appear in error messages.
    """
    if not error_msg:
        return "Unknown error"

    # List of patterns that might contain sensitive data
    sensitive_patterns = ['api_key', 'apikey', 'api-key', 'bearer', 'token', 'password', 'secret']

    # Convert to string and lowercase for checking
    error_lower = str(error_msg).lower()

    # If error contains sensitive patterns, return generic message
    for pattern in sensitive_patterns:
        if pattern in error_lower:
            return "Request failed (details logged server-side)"

    return str(error_msg)


def litellm_request(path, method="GET", data=None):
    """Make request to LiteLLM API with logging for debugging."""
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

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        # Log full details server-side for debugging
        print(f"[ERROR] LiteLLM request failed: {method} {path} -> HTTP {e.code}", flush=True)
        try:
            error_body = e.read().decode()
            print(f"[ERROR] Response: {error_body[:500]}", flush=True)
        except:
            pass
        return {"error": _sanitize_error(str(e)), "status": e.code}
    except urllib.error.URLError as e:
        print(f"[ERROR] LiteLLM connection failed: {method} {path} -> {e.reason}", flush=True)
        return {"error": "LiteLLM is not reachable. Is it running?", "offline": True}
    except Exception as e:
        print(f"[ERROR] LiteLLM request error: {method} {path} -> {e}", flush=True)
        return {"error": _sanitize_error(str(e))}

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
        """Read and parse JSON body from request.

        Returns:
            dict: Parsed JSON data, or empty dict on error
        """
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

            # System is "online" if LiteLLM is running AND at least one provider has API keys
            # Note: This indicates system readiness, not a specific provider's status
            any_provider_available = litellm_alive and has_any_api_keys()

            self.send_json({
                "accounts": safe_accounts,
                "providers": providers_with_status,
                "models": models,
                "presets": [],
                "config": {},
                "emulatorActive": emulator_active,
                "providerOnline": any_provider_available  # True if any provider is configured
            })

        elif path == "/emulator/status":
            health = litellm_request("/health")
            litellm_alive = "error" not in health

            model_info = litellm_request("/model/info")
            active_emulations = get_active_emulations(model_info)

            # System is "online" if LiteLLM is running AND at least one provider has API keys
            # Note: This indicates system readiness, not a specific provider's status
            any_provider_available = litellm_alive and has_any_api_keys()

            self.send_json({
                "emulatorRunning": len(active_emulations) > 0,
                "providerOnline": any_provider_available,  # True if any provider is configured
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

        elif path == "/providers/list":
            # Return list of all supported providers (for dynamic frontend use)
            self.send_json({"providers": PROVIDERS})

        elif path == "/models":
            provider = query.get("provider", [""])[0]
            models = []

            # Query LiteLLM proxy for available models
            result = litellm_request("/v1/models")

            # Check if LiteLLM is offline
            if "offline" in result or "error" in result:
                error_msg = result.get("error", "LiteLLM is not available")
                self.send_json({
                    "models": [],
                    "error": error_msg,
                    "offline": result.get("offline", False)
                })
                return

            if "data" in result:
                provider_info = get_provider_by_id(provider) if provider else None
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

            # Save account FIRST (file operation - can rollback if API fails)
            new_account = {
                "provider": provider,
                "accountName": account_name,
                "apiKey": api_key
            }
            accounts.append(new_account)
            try:
                save_accounts(accounts)
            except Exception as e:
                self.send_json({"success": False, "error": f"Failed to save account: {e}"}, 500)
                return

            # Add wildcard route AFTER save succeeds (rollback on failure)
            if is_first_account:
                result = add_wildcard_to_database(provider, api_key)
                if "error" in result:
                    # Rollback: remove the account we just saved
                    accounts = [a for a in accounts if not (a["provider"] == provider and a["accountName"] == account_name)]
                    try:
                        save_accounts(accounts)
                    except Exception:
                        pass  # Best effort rollback
                    self.send_json({"success": False, "error": result.get("error")}, 500)
                    return

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
            deleted = False
            if len(remaining_accounts) == 0:
                # Remove wildcard route from database
                deleted = remove_wildcard_from_database(provider)

            self.send_json({"success": True, "deleted": deleted})

        elif path == "/emulator/start":
            """
            Start model emulation by registering explicit model mapping in database.

            Request format:
            {
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "emulatedModelName": "gpt-4",
                "account": "account-name" (optional)
            }
            """
            data = self.read_json_body()
            account_name = data.get("account", "").strip()
            provider = data.get("provider", "").strip()
            model = data.get("model", "").strip()
            emulated_name = data.get("emulatedModelName", model)

            # Validate and clean emulated name
            if emulated_name:
                emulated_name = emulated_name.strip()

            if not provider or not model:
                self.send_json({"success": False, "error": "Provider and model required"}, 400)
                return

            if not emulated_name:
                self.send_json({"success": False, "error": "Emulated model name required (cannot be empty or whitespace)"}, 400)
                return

            # Find API key using helper
            api_key = find_api_key_for_provider(provider, account_name)

            if not api_key:
                self.send_json({"success": False, "error": "No API key found for provider"}, 400)
                return

            # Get provider prefix
            prov = get_provider_by_id(provider)
            prefix = prov["prefix"] if prov else ""
            full_model = f"{prefix}{model}"

            # Register emulation via /model/new API
            # model_name: What user requests (e.g., "gpt-4")
            # litellm_params.model: What actually gets called (e.g., "groq/llama-3.3-70b-versatile")
            model_data = {
                "model_name": emulated_name,
                "litellm_params": {
                    "model": full_model,
                    "api_key": api_key
                }
            }

            result = litellm_request("/model/new", method="POST", data=model_data)

            if "error" in result:
                self.send_json({
                    "success": False,
                    "error": _sanitize_error(result.get("error"))
                }, 500)
            else:
                model_id = result.get("model_info", {}).get("id")
                print(f"[INFO] Started emulation: {emulated_name} → {full_model}", flush=True)
                self.send_json({
                    "success": True,
                    "modelId": model_id,
                    "emulatedName": emulated_name,
                    "actualModel": full_model
                })

        elif path == "/emulator/stop":
            """
            Stop all active emulations by deleting explicit model mappings.
            Wildcard routes remain active.
            """
            # Get all registered models
            models_info = litellm_request("/model/info")

            if "error" in models_info:
                self.send_json({
                    "success": False,
                    "error": _sanitize_error(models_info.get("error"))
                }, 500)
                return

            deleted_count = 0
            emulations = []

            # Iterate through all models
            for model_data in models_info.get("data", []):
                model_info = model_data.get("model_info", {})
                model_name = model_info.get("model_name", "")
                litellm_params = model_data.get("litellm_params", {})
                actual_model = litellm_params.get("model", "")

                # Skip wildcard routes (these are NOT emulations)
                if is_wildcard_model(model_name):
                    continue

                # This is an emulation if model_name != actual_model
                # Example: model_name="gpt-4", actual_model="groq/llama-3.3-70b-versatile"
                if model_name != actual_model:
                    model_id = model_info.get("id")

                    # Validate model_id format (must be non-empty string, typically UUID)
                    if not model_id or not isinstance(model_id, str) or len(model_id.strip()) == 0:
                        print(f"[WARN] Skipping invalid model_id for {model_name}: {model_id}", flush=True)
                        continue

                    # Validate UUID format (LiteLLM uses UUIDs for database IDs)
                    try:
                        uuid.UUID(model_id)
                    except ValueError:
                        print(f"[WARN] Skipping non-UUID model_id for {model_name}: {model_id}", flush=True)
                        continue

                    # Delete this emulation
                    result = litellm_request("/model/delete", method="POST",
                                           data={"id": model_id})

                    if "error" in result:
                        print(f"[WARN] Failed to delete model {model_id}: {result.get('error')}", flush=True)
                        continue

                    deleted_count += 1
                    emulations.append({
                        "emulatedName": model_name,
                        "actualModel": actual_model
                    })
                    print(f"[INFO] Stopped emulation: {model_name} → {actual_model}", flush=True)

            self.send_json({
                "success": True,
                "deleted": deleted_count,
                "emulations": emulations
            })

        else:
            self.send_json({"error": "Not found"}, 404)

def main():
    with socketserver.TCPServer(("127.0.0.1", PORT), APIHandler) as httpd:
        print(f"http://localhost:{PORT}/config.html", flush=True)
        httpd.serve_forever()

if __name__ == "__main__":
    main()
