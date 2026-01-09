"""
Virtual Model Emulator v2.2.2 - Backend Server
OpenAI-compatible endpoint powered by LiteLLM SDK.
Uses LiteLLM SDK directly (no proxy needed).
"""
import json
import os
import http.server
import socketserver
import ssl
import threading
import time
import gzip
import logging
import traceback
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from datetime import datetime

from cryptography.fernet import Fernet
import yaml

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
CONFIG_FILE = CONFIG_DIR / "config.yaml"
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"
EMULATIONS_FILE = CONFIG_DIR / "emulations.json"

# AUDIT LOGGING
audit_log_file = CONFIG_DIR / "audit.log"
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler(audit_log_file)
audit_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

# ERROR LOGGING
error_log_file = CONFIG_DIR / "errors.log"
error_logger = logging.getLogger('errors')
error_handler = logging.FileHandler(error_log_file)
error_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(funcName)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)

class ModelCache:
    """Cache provider model lists with 1-hour TTL (thread-safe)"""
    def __init__(self, ttl_seconds=3600):
        self.cache = {}
        self.ttl = ttl_seconds
        self.lock = threading.Lock()

    def get(self, provider: str) -> Optional[List[Dict]]:
        with self.lock:
            if provider not in self.cache:
                return None
            cached = self.cache[provider]
            age = time.time() - cached['timestamp']
            if age > self.ttl:
                del self.cache[provider]
                return None
            return cached['models']

    def set(self, provider: str, models: List[Dict]) -> None:
        with self.lock:
            self.cache[provider] = {
                'models': models,
                'timestamp': time.time()
            }

    def invalidate(self, provider: Optional[str] = None) -> None:
        with self.lock:
            if provider:
                self.cache.pop(provider, None)
            else:
                self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'cached_providers': len(self.cache),
                'entries': {p: len(v['models']) for p, v in self.cache.items()}
            }

class CachedFallback:
    """Fall back to stale cache if provider is down"""
    def __init__(self):
        self.stale_cache = {}

    def save_stale(self, provider: str, models: List[Dict]) -> None:
        self.stale_cache[provider] = {
            'models': models,
            'timestamp': time.time()
        }

    def get_stale(self, provider: str) -> Optional[List[Dict]]:
        return self.stale_cache.get(provider, {}).get('models')

    def age_minutes(self, provider: str) -> Optional[int]:
        if provider not in self.stale_cache:
            return None
        age_seconds = time.time() - self.stale_cache[provider]['timestamp']
        return int(age_seconds / 60)

class RateLimiter:
    """Simple rate limiter for API endpoints (thread-safe)"""
    def __init__(self, requests_per_second=10):
        self.requests_per_second = requests_per_second
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        with self.lock:
            now = time.time()
            window_start = now - 1.0
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip] if ts > window_start
            ]
            if len(self.requests[client_ip]) >= self.requests_per_second:
                return False
            self.requests[client_ip].append(now)
            return True

def log_audit(action: str, provider: str, account_name: str, success: bool, details: str = "") -> None:
    """Log security-relevant actions"""
    status = "SUCCESS" if success else "FAILED"
    msg = f"{action} | Provider={provider} | Account={account_name} | {status}"
    if details:
        msg += f" | {details}"
    audit_logger.info(msg)

def log_error(error: Exception, context: Dict[str, Any], action: str) -> None:
    """Log error with structured context"""
    error_logger.error(
        f"{action} | Error={type(error).__name__} | "
        f"Message={str(error)[:100]} | "
        f"Context={json.dumps(context, default=str)}"
    )

def should_retry(error: Exception) -> bool:
    """Determine if error is transient and retryable"""
    error_str = str(error).lower()
    transient_patterns = [
        'timeout', 'connection', 'rate limit', 'temporarily unavailable',
        '502', '503', '504'
    ]
    return any(pattern in error_str for pattern in transient_patterns)

def call_with_retry(func, *args, max_attempts: int = 3, base_delay: float = 1.0, **kwargs) -> Any:
    """Call function with exponential backoff retry"""
    last_error = None
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if not should_retry(e):
                raise
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"[WARN] Retrying (attempt {attempt + 1}/{max_attempts}): delay={delay:.1f}s", flush=True)
            time.sleep(delay)
    raise last_error

model_cache = ModelCache(ttl_seconds=3600)
stale_fallback = CachedFallback()
rate_limiter = RateLimiter(requests_per_second=10)

# Thread-safe lock for emulation operations
_emulation_lock = threading.Lock()


class CORSHandler:
    """Production-ready CORS handler with secure defaults and optional config override"""

    # Default origins that should always work for local development
    DEFAULT_ALLOWED_ORIGINS = {
        "http://localhost:8775",      # Your emulator's own UI
        "http://127.0.0.1:8775",      # Same as above, IP format
        "http://localhost:3000",       # Common Open WebUI/Next.js port
        "http://localhost:8080",       # Common dev server port
        "http://localhost:42004",      # Your current Open WebUI port
        "http://127.0.0.1:3000",       # IP format for Open WebUI
        "http://127.0.0.1:8080",       # IP format for other dev servers
    }

    # Allow any localhost port for development convenience
    # (Comment this out for production deployment)
    LOCALHOST_WILDCARD = True

    def __init__(self):
        self.allowed_origins = self._load_configured_origins()
        self.allowed_methods = {"GET", "POST", "OPTIONS"}
        self.allowed_headers = {"Content-Type", "Authorization", "X-Requested-With"}
        print(f"[INFO] CORS enabled for {len(self.allowed_origins)} allowed origins", flush=True)

    def _load_configured_origins(self):
        """Load origins - config file can extend defaults but not replace them"""
        origins = set(self.DEFAULT_ALLOWED_ORIGINS)

        # Optional: Allow config.yaml to ADD origins (but defaults always included)
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config = yaml.safe_load(f) or {}
                    extra_origins = config.get('general_settings', {}).get('allowed_origins', [])
                    origins.update(extra_origins)
                    if extra_origins:
                        print(f"[INFO] Added {len(extra_origins)} CORS origins from config", flush=True)
        except Exception as e:
            print(f"[WARN] Could not load CORS config: {e}", flush=True)

        return origins

    def is_origin_allowed(self, origin):
        """Validate origin against allowlist with smart localhost handling"""
        if not origin:
            return False

        # 1. Exact match in allowed origins
        if origin in self.allowed_origins:
            return True

        # 2. Development convenience: allow any localhost port
        if self.LOCALHOST_WILDCARD:
            if origin.startswith(('http://localhost:', 'http://127.0.0.1:')):
                print(f"[DEBUG] Allowing localhost origin: {origin}", flush=True)
                return True

        # 3. Optional: Domain pattern matching for production
        # if any(origin.startswith(pattern) for pattern in self.domain_patterns):
        #     return True

        print(f"[SECURITY] CORS blocked origin: {origin}", flush=True)
        return False

    def add_cors_headers(self, handler, origin):
        """Add CORS headers to response"""
        if self.is_origin_allowed(origin):
            handler.send_header("Access-Control-Allow-Origin", origin)
            handler.send_header("Access-Control-Allow-Credentials", "true")
            return True
        return False

    def handle_preflight(self, handler):
        """Handle CORS preflight OPTIONS request"""
        origin = handler.headers.get('Origin', '')

        if not self.is_origin_allowed(origin):
            handler.send_error(403, "Origin not allowed")
            return False

        handler.send_response(200)
        self.add_cors_headers(handler, origin)
        handler.send_header("Access-Control-Allow-Methods", ", ".join(self.allowed_methods))
        handler.send_header("Access-Control-Allow-Headers", ", ".join(self.allowed_headers))
        handler.send_header("Access-Control-Max-Age", "86400")  # 24 hours
        handler.end_headers()
        return True


class AccountEncryption:
    """Handle encryption/decryption of API keys using master key from config.yaml"""

    def __init__(self):
        # First, ensure config directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get or create master key
        self.master_key = self._get_or_create_master_key()
        self.cipher = Fernet(self.master_key)
        print(f'[OK] Encryption initialized with key', flush=True)

    def _get_or_create_master_key(self):
        """Get master key from config.yaml - create one-time permanent key on first install"""
        try:
            # 1. Try to load existing config
            config = {}
            if CONFIG_FILE.exists():
                print(f'[DEBUG] config.yaml exists, attempting to load', flush=True)
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f) or {}
                        print(f'[DEBUG] Loaded config, keys: {list(config.keys())}', flush=True)
                except Exception as e:
                    print(f'[ERROR] Failed to load config.yaml: {e}', flush=True)
                    config = {}
            
            # 2. Check if we have a master_key in the proper location
            # First check old location (root) for backward compatibility
            master_key = None
            if 'master_key' in config:
                # Old format - migrate to new format
                print(f'[INFO] Found master_key at root, migrating to general_settings', flush=True)
                master_key = config['master_key']
                # Move it to general_settings
                if 'general_settings' not in config:
                    config['general_settings'] = {}
                config['general_settings']['master_key'] = master_key
                del config['master_key']
            elif config.get('general_settings', {}).get('master_key'):
                # New format - already in general_settings
                master_key = config['general_settings']['master_key']
                print(f'[DEBUG] Found master_key in general_settings', flush=True)
            
            # 3. If no key exists, generate new one and create full config structure
            if not master_key:
                print(f'[INFO] No master_key found, generating new permanent key', flush=True)
                new_key = Fernet.generate_key().decode()
                
                # Build complete config structure
                config = {
                    'model_list': [],
                    'general_settings': {
                        'master_key': new_key,
                    },
                    'litellm_settings': {
                        'drop_params': True,
                        'check_provider_endpoint': True,
                        'cost_tracking': False
                    }
                }
                master_key = new_key
                print(f'[DEBUG] Created new config structure with master_key', flush=True)
            else:
                # Key exists, ensure full structure is present
                if 'model_list' not in config:
                    config['model_list'] = []
                if 'general_settings' not in config:
                    config['general_settings'] = {}
                if 'litellm_settings' not in config:
                    config['litellm_settings'] = {
                        'drop_params': True,
                        'check_provider_endpoint': True,
                        'cost_tracking': False
                    }
            
            # 4. Save the config to file (always save to ensure structure is correct)
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                print(f'[OK] Master key ready in config.yaml', flush=True)
                
                # Verify file was written
                if CONFIG_FILE.exists():
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if master_key in content:
                            print(f'[DEBUG] Master key confirmed in config.yaml', flush=True)
            except Exception as e:
                print(f'[CRITICAL] Failed to write config.yaml: {e}', flush=True)
                import traceback
                traceback.print_exc()
                raise
            
            return master_key.encode()
            
        except Exception as e:
            print(f'[FATAL] Failed to initialize master key: {e}', flush=True)
            # Fallback: generate an ephemeral key for this session only
            print(f'[WARN] Using ephemeral key for this session', flush=True)
            return Fernet.generate_key()

    def encrypt(self, plaintext):
        """Encrypt API key"""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext):
        """Decrypt API key"""
        try:
            return self.cipher.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            print(f'[ERROR] Failed to decrypt API key: {e}', flush=True)
            return None


# Initialize encryption at module level
encryption = AccountEncryption()

# CORS handler with secure defaults
cors_handler = CORSHandler()

# In-memory emulation state (persisted to JSON)
_active_emulations = []

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)


def load_accounts() -> List[Dict[str, Any]]:
    """Load accounts from JSON file and decrypt API keys."""
    if ACCOUNTS_FILE.exists():
        try:
            accounts = json.loads(ACCOUNTS_FILE.read_text())
            # Decrypt API keys on load
            for acc in accounts:
                if 'apiKey' in acc:
                    decrypted = encryption.decrypt(acc['apiKey'])
                    if decrypted:
                        acc['apiKey'] = decrypted
            return accounts
        except Exception as e:
            print(f'[WARN] Failed to load accounts: {e}', flush=True)
    return []


def save_accounts(accounts: List[Dict[str, Any]]) -> None:
    """Save accounts to JSON file with encrypted API keys (atomic)."""
    accounts_to_save = []
    for acc in accounts:
        acc_copy = acc.copy()
        if 'apiKey' in acc_copy:
            acc_copy['apiKey'] = encryption.encrypt(acc_copy['apiKey'])
        accounts_to_save.append(acc_copy)

    try:
        # Write to temp file first, then rename (atomic)
        temp_file = ACCOUNTS_FILE.with_suffix('.json.tmp')
        temp_file.write_text(json.dumps(accounts_to_save, indent=2))
        temp_file.replace(ACCOUNTS_FILE)
        try:
            ACCOUNTS_FILE.chmod(0o600)
        except Exception as e:
            print(f"[WARN] Could not set accounts.json permissions: {e}", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to save accounts: {e}", flush=True)
        log_error(e, {"action": "save_accounts"}, "SAVE_ACCOUNTS_FAILED")
        raise


def load_emulations() -> List[Dict[str, Any]]:
    """Load emulations from JSON file with validation."""
    global _active_emulations
    try:
        if EMULATIONS_FILE.exists():
            content = EMULATIONS_FILE.read_text()
            _active_emulations = json.loads(content)
            if isinstance(_active_emulations, list) and len(_active_emulations) > 0:
                print(f"[OK] Loaded {len(_active_emulations)} emulations from disk", flush=True)
            return _active_emulations
    except json.JSONDecodeError as e:
        print(f"[ERROR] Corrupted emulations.json: {e}", flush=True)
        print(f"[WARN] Starting with empty emulations", flush=True)
    except Exception as e:
        print(f"[WARN] Failed to load emulations: {e}", flush=True)

    _active_emulations = []
    return []


def save_emulations() -> None:
    """Save emulations to JSON file (atomic)."""
    global _active_emulations
    try:
        temp_file = EMULATIONS_FILE.with_suffix('.json.tmp')
        temp_file.write_text(json.dumps(_active_emulations, indent=2))
        temp_file.replace(EMULATIONS_FILE)
        try:
            EMULATIONS_FILE.chmod(0o600)
        except Exception as e:
            print(f"[WARN] Could not set emulations.json permissions: {e}", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to save emulations: {e}", flush=True)
        log_error(e, {"action": "save_emulations"}, "SAVE_EMULATIONS_FAILED")
        raise


def get_accounts_for_provider(provider_id: str) -> List[Dict[str, Any]]:
    """Get all accounts for a specific provider."""
    accounts = load_accounts()
    return [a for a in accounts if a["provider"] == provider_id]


def get_providers_with_accounts() -> List[str]:
    """Get list of provider IDs that have at least one account."""
    accounts = load_accounts()
    return list(set(acc["provider"] for acc in accounts))


def get_provider_by_id(provider_id: Optional[str]) -> Optional[Dict[str, str]]:
    """Get provider info by ID."""
    if not provider_id or not isinstance(provider_id, str):
        return None
    return next((p for p in PROVIDERS if p["id"] == provider_id), None)


def find_api_key_for_provider(provider_id: str, account_name: Optional[str] = None) -> Optional[str]:
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


def has_any_api_keys() -> bool:
    """Check if ANY provider has an API key configured."""
    accounts = load_accounts()
    if len(accounts) > 0:
        return True
    return any(os.environ.get(p["envVar"]) for p in PROVIDERS)


def _sanitize_error(error_msg: Any) -> str:
    """Remove potentially sensitive information from error messages."""
    if not error_msg:
        return "Unknown error"

    error_str = str(error_msg)
    error_lower = error_str.lower()

    # List of sensitive patterns to look for
    sensitive_patterns = [
        'api_key', 'apikey', 'api-key', 'api_token', 'apitoken',
        'bearer', 'token', 'password', 'secret', 'authorization',
        'auth=', 'key=', 'x-api-key', 'sk-', 'sk_', 'pk-', 'pk_'
    ]

    for pattern in sensitive_patterns:
        if pattern in error_lower:
            # Generic message - sensitive pattern detected
            return "Request failed (sensitive data detected - details logged server-side)"

    # If no sensitive patterns, return first 200 chars
    if len(error_str) > 200:
        return error_str[:200] + "..."

    return error_str


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

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def send_json(self, data, status=200):
        json_str = json.dumps(data)
        json_bytes = json_str.encode()
        origin = self.headers.get('Origin', '')

        # Compress if > 1KB
        if len(json_bytes) > 1024:
            compressed = gzip.compress(json_bytes)
            if len(compressed) < len(json_bytes):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Encoding", "gzip")
                cors_handler.add_cors_headers(self, origin)
                self.send_header("Content-Security-Policy", "default-src 'self'")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(compressed)
                return

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        cors_handler.add_cors_headers(self, origin)
        self.send_header("Content-Security-Policy", "default-src 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(json_bytes)

    def read_json_body(self, max_size=10_485_760):  # 10MB limit
        """Read and parse JSON body from request (with size limit)."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > max_size:
                return None  # Caller should check for None
            if content_length:
                raw_body = self.rfile.read(content_length)
                return json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[WARN] Failed to parse JSON body: {e}", flush=True)
        except Exception as e:
            print(f"[WARN] Unexpected error reading request body: {e}", flush=True)
        return {}

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        if not cors_handler.handle_preflight(self):
            return  # Error already sent

    def do_GET(self):
        import urllib.parse
        global _active_emulations

        # Rate limiting
        client_ip = self.client_address[0]
        if not rate_limiter.is_allowed(client_ip):
            self.send_json({"error": "Rate limit exceeded. Max 10 req/s"}, 429)
            log_audit("RATE_LIMIT_EXCEEDED", "", "", False, f"IP={client_ip}")
            return

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
            with _emulation_lock:
                safe_emulations = [
                    {k: v for k, v in e.items() if k != "apiKey"}
                    for e in _active_emulations
                ]
            self.send_json({"active": safe_emulations, "count": len(safe_emulations)})

        elif path == "/providers/list":
            self.send_json({"providers": PROVIDERS})

        elif path == "/models":
            import requests

            provider = query.get("provider", [""])[0]
            force = query.get("force", ["false"])[0].lower() == "true"

            if not provider:
                self.send_json({"error": "provider parameter required"}, 400)
                return

            if not force:
                cached_models = model_cache.get(provider)
                if cached_models is not None:
                    self.send_json({"models": cached_models, "cached": True})
                    return

            try:
                provider_db_path = CONFIG_DIR / "providers_models.json"
                if not provider_db_path.exists():
                    self.send_json({"error": "Provider database not found", "models": []}, 500)
                    return

                with open(provider_db_path, 'r') as f:
                    provider_db = json.load(f)

                if provider not in provider_db.get("providers", {}):
                    self.send_json({"error": f"Unknown provider: {provider}", "models": []}, 400)
                    return

                provider_config = provider_db["providers"][provider]
                api_key = find_api_key_for_provider(provider)

                if not api_key:
                    self.send_json({"error": f"No API key configured for {provider}", "models": []}, 400)
                    return

                models_list = []

                if provider_config.get("endpoint_type") == "openai_compatible" and provider_config.get("models_endpoint"):
                    models_endpoint = provider_config["models_endpoint"]
                    auth_format = provider_config.get("auth_format", "Bearer {api_key}").format(api_key=api_key)
                    response = call_with_retry(requests.get, models_endpoint, headers={"Authorization": auth_format}, timeout=15, max_attempts=3)
                    response.raise_for_status()
                    models_list = [m["id"] for m in response.json().get("data", [])]
                elif provider_config.get("static_models"):
                    models_list = provider_config["static_models"]
                else:
                    raise ValueError(f"Model discovery not available for {provider}")

                formatted_models = []
                prov = get_provider_by_id(provider)
                for model_id in models_list:
                    formatted_models.append({
                        "id": model_id,
                        "label": model_id,
                        "provider": provider,
                        "providerName": prov["name"] if prov else provider_config.get("name", provider)
                    })

                formatted_models.sort(key=lambda m: m.get("label", "").lower())
                model_cache.set(provider, formatted_models)
                stale_fallback.save_stale(provider, formatted_models)
                self.send_json({"models": formatted_models, "cached": False})

            except Exception as e:
                stale_models = stale_fallback.get_stale(provider)
                if stale_models:
                    age = stale_fallback.age_minutes(provider)
                    log_error(e, {"provider": provider, "stale_age_minutes": age}, "MODELS_FALLBACK_TO_STALE")
                    self.send_json({"models": stale_models, "cached": True, "warning": f"Using cached data from {age} minutes ago"})
                else:
                    log_error(e, {"provider": provider, "endpoint": path}, "MODEL_FETCH_FAILED")
                    self.send_json({"error": _sanitize_error(str(e)), "offline": True, "models": []}, 400)

        elif path == "/v1/models":
            """OpenAI-compatible models endpoint for Open WebUI"""
            with _emulation_lock:
                # Format emulations into OpenAI's model list structure
                model_list = []
                for emulation in _active_emulations:
                    model_list.append({
                        "id": emulation["emulatedName"],  # The name Open WebUI will see
                        "object": "model",
                        "created": int(time.time()),  # Current timestamp
                        "owned_by": "virtual-model-emulator"
                    })
            
            self.send_json({
                "object": "list",
                "data": model_list
            })
                
        elif path == "/admin/cache-stats":
            self.send_json({
                "cache": model_cache.stats(),
                "ttl_seconds": model_cache.ttl
            })

        elif path == "/admin/master-key":
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    # Check both old and new locations
                    master_key = config.get('general_settings', {}).get('master_key', config.get('master_key', ''))
                
                if master_key:
                    self.send_json({"masterKey": master_key})
                else:
                    self.send_json({"error": "Master key not found"}, 500)
            except Exception as e:
                log_error(e, {"action": "get_master_key"}, "GET_MASTER_KEY_FAILED")
                self.send_json({"error": "Failed to retrieve master key"}, 500)

        elif path == "/" or path == "":
            self.path = "/config.html"
            super().do_GET()

        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
        import urllib.parse
        import uuid
        global _active_emulations

        # Rate limiting
        client_ip = self.client_address[0]
        if not rate_limiter.is_allowed(client_ip):
            self.send_json({"error": "Rate limit exceeded. Max 10 req/s"}, 429)
            log_audit("RATE_LIMIT_EXCEEDED", "", "", False, f"IP={client_ip}")
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/providers/connect":
            data = self.read_json_body()
            if data is None:
                self.send_json({"error": "Request body too large (max 10MB)"}, 413)
                return

            provider = data.get("provider")
            account_name = data.get("accountName")
            api_key = data.get("apiKey")

            # Validate provider is in PROVIDERS list
            valid_providers = [p["id"] for p in PROVIDERS]
            if provider not in valid_providers:
                log_audit("ACCOUNT_ADD_FAILED", provider or "", "", False, "Invalid provider")
                self.send_json({"success": False, "error": f"Unknown provider: {provider}"}, 400)
                return

            if not all([provider, account_name, api_key]):
                log_audit("ACCOUNT_ADD_FAILED", provider or "", account_name or "", False, "Missing fields")
                self.send_json({"success": False, "error": "Missing required fields"}, 400)
                return

            accounts = load_accounts()

            # Check for duplicate
            for acc in accounts:
                if acc["provider"] == provider and acc["accountName"] == account_name:
                    log_audit("ACCOUNT_ADD_FAILED", provider, account_name, False, "Already exists")
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
            model_cache.invalidate(provider)  # Invalidate cache when new account added
            log_audit("ACCOUNT_ADDED", provider, account_name, True)
            print(f"[OK] Connected provider: {provider}/{account_name}", flush=True)
            self.send_json({"success": True})

        elif path == "/providers/disconnect":
            data = self.read_json_body()
            provider = data.get("provider")
            account_name = data.get("accountName")

            accounts = load_accounts()
            accounts = [a for a in accounts if not (a["provider"] == provider and a["accountName"] == account_name)]
            save_accounts(accounts)
            model_cache.invalidate(provider)
            log_audit("ACCOUNT_REMOVED", provider, account_name, True)
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
                log_audit("EMULATION_START_FAILED", provider, account_name, False, "Missing provider/model")
                self.send_json({"success": False, "error": "Provider and model required"}, 400)
                return

            if not emulated_name:
                log_audit("EMULATION_START_FAILED", provider, account_name, False, "Missing emulated name")
                self.send_json({"success": False, "error": "Emulated model name required"}, 400)
                return

            # Find API key
            api_key = find_api_key_for_provider(provider, account_name)
            if not api_key:
                log_audit("EMULATION_START_FAILED", provider, account_name, False, "No API key")
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
                "apiKey": encryption.encrypt(api_key)
            }

            with _emulation_lock:
                _active_emulations = [e for e in _active_emulations if e["emulatedName"] != emulated_name]
                _active_emulations.append(emulation)
                save_emulations()

            log_audit("EMULATION_START", provider, account_name, True, f"Model={model}→{full_model}")
            print(f"[OK] Started emulation: {emulated_name} → {full_model}", flush=True)
            self.send_json({
                "success": True,
                "modelId": emulation_id,
                "emulatedName": emulated_name,
                "actualModel": full_model
            })

        elif path == "/emulator/stop":
            """Stop all active emulations (authenticated only)."""
            admin_secret = os.environ.get('ADMIN_SECRET')
            if admin_secret:
                auth_header = self.headers.get('Authorization', '')
                if auth_header != f'Bearer {admin_secret}':
                    self.send_json({"error": "Unauthorized"}, 403)
                    log_audit("EMULATOR_STOP_UNAUTHORIZED", "", "", False, f"IP={client_ip}")
                    return

            with _emulation_lock:
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
            if data is None:
                self.send_json({"error": "Request body too large (max 10MB)"}, 413)
                return

            requested_model = data.get("model", "")
            messages = data.get("messages", [])

            if not messages:
                self.send_json({"error": "Messages required"}, 400)
                return

            # Validate each message has required fields
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    self.send_json({"error": f"Message {i} must be object"}, 400)
                    return
                if "role" not in msg or "content" not in msg:
                    self.send_json({"error": f"Message {i} missing role or content"}, 400)
                    return
                if msg.get("role") not in ["user", "assistant", "system"]:
                    self.send_json({"error": f"Message {i} invalid role"}, 400)
                    return

            # Validate temperature
            temperature = data.get("temperature", 0.7)
            try:
                temperature = float(temperature)
                if not (0.0 <= temperature <= 2.0):
                    raise ValueError(f"temperature must be 0.0-2.0, got {temperature}")
            except (ValueError, TypeError) as e:
                self.send_json({"error": f"Invalid temperature: {e}"}, 400)
                return

            # Validate max_tokens
            max_tokens = data.get("max_tokens")
            if max_tokens is not None:
                try:
                    max_tokens = int(max_tokens)
                    if max_tokens <= 0:
                        raise ValueError(f"max_tokens must be positive")
                    if max_tokens > 32000:
                        raise ValueError(f"max_tokens cannot exceed 32000")
                except (ValueError, TypeError) as e:
                    self.send_json({"error": f"Invalid max_tokens: {e}"}, 400)
                    return

            # Find emulation for requested model
            emulation = None
            api_key = None
            actual_model = requested_model

            with _emulation_lock:
                for em in _active_emulations:
                    if em["emulatedName"] == requested_model:
                        emulation = em
                        actual_model = em["actualModel"]
                        # Decrypt API key from emulation
                        api_key = encryption.decrypt(em["apiKey"])
                        break

            # If no emulation found, try to use the model directly
            if not emulation:
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
                response = call_with_retry(
                    litellm.completion,
                    model=actual_model,
                    messages=messages,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    timeout=30,
                    max_attempts=3,
                    base_delay=1.0
                )

                result = {
                    "id": response.id,
                    "object": "chat.completion",
                    "created": response.created,
                    "model": requested_model,
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
                context = {
                    "model": requested_model,
                    "actual_model": actual_model,
                    "client_ip": self.client_address[0]
                }
                log_error(e, context, "CHAT_COMPLETION_FAILED")
                self.send_json({
                    "error": {
                        "message": _sanitize_error(str(e)),
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

    # Load and validate emulations from file
    emulations = load_emulations()
    if len(emulations) > 0:
        print(f"[INFO] Restored {len(emulations)} active emulations from disk", flush=True)

    # Ensure required directories exist
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Verify configuration is ready
    accounts = load_accounts()
    if len(accounts) == 0:
        print(f"[INFO] No accounts configured yet - use connect.html to add providers", flush=True)
    else:
        print(f"[INFO] Loaded {len(accounts)} provider account(s)", flush=True)

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
            # Optional: Enable SSL if cert available
            ssl_cert = os.environ.get('SSL_CERT_FILE')
            ssl_key = os.environ.get('SSL_KEY_FILE')
            if ssl_cert and ssl_key:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(ssl_cert, ssl_key)
                httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
                print(f"[OK] HTTPS enabled", flush=True)
                print(f"https://localhost:{port}/config.html", flush=True)
            else:
                print(f"[INFO] HTTPS disabled (set SSL_CERT_FILE and SSL_KEY_FILE to enable)", flush=True)
                print(f"http://localhost:{port}/config.html", flush=True)

            print(f"[INFO] API server started on port {port}", flush=True)
            print(f"[INFO] Architecture: API Server → LiteLLM SDK → Provider APIs", flush=True)
            print(f"[OK] Server ready - No proxy or database needed!", flush=True)
            print(f"[OK] All services started and verified", flush=True)
            httpd.serve_forever()

    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"[ERROR] Port {port} is already in use", flush=True)
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()



