"""
Configuration manager for the model emulator

This module handles:
- Generating LiteLLM config.yaml from accounts
- Encrypting/decrypting API keys in accounts.json
- Managing environment variables for LiteLLM subprocess
"""

import base64
import json
import os
import random
import string
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import cryptography for encryption
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Paths
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_PATH = CONFIG_DIR / "default.json"
ACCOUNTS_PATH = CONFIG_DIR / "accounts.json"
SECRET_PATH = CONFIG_DIR / ".secret"
LITELLM_CONFIG_PATH = CONFIG_DIR / "config.yaml"
SAVED_CONFIGS_PATH = CONFIG_DIR / "saved-configs.json"

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Provider registry - defines known providers and their configurations
PROVIDER_REGISTRY = {
    "openai": {
        "name": "OpenAI",
        "envVar": "OPENAI_API_KEY",
        "prefix": "openai/",
        "models": [
            {"id": "gpt-4", "label": "GPT-4"},
            {"id": "gpt-4-turbo", "label": "GPT-4 Turbo"},
            {"id": "gpt-4o", "label": "GPT-4o"},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
            {"id": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"},
            {"id": "o1", "label": "o1"},
            {"id": "o1-mini", "label": "o1 Mini"},
        ]
    },
    "anthropic": {
        "name": "Anthropic",
        "envVar": "ANTHROPIC_API_KEY",
        "prefix": "anthropic/",
        "models": [
            {"id": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku"},
            {"id": "claude-3-opus-20240229", "label": "Claude 3 Opus"},
            {"id": "claude-3-sonnet-20240229", "label": "Claude 3 Sonnet"},
            {"id": "claude-3-haiku-20240307", "label": "Claude 3 Haiku"},
        ]
    },
    "groq": {
        "name": "Groq",
        "envVar": "GROQ_API_KEY",
        "prefix": "groq/",
        "models": [
            {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B"},
            {"id": "llama-3.1-70b-versatile", "label": "Llama 3.1 70B"},
            {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B"},
            {"id": "mixtral-8x7b-32768", "label": "Mixtral 8x7B"},
            {"id": "gemma2-9b-it", "label": "Gemma 2 9B"},
        ]
    },
    "mistral": {
        "name": "Mistral",
        "envVar": "MISTRAL_API_KEY",
        "prefix": "mistral/",
        "models": [
            {"id": "mistral-large-latest", "label": "Mistral Large"},
            {"id": "mistral-medium-latest", "label": "Mistral Medium"},
            {"id": "mistral-small-latest", "label": "Mistral Small"},
            {"id": "codestral-latest", "label": "Codestral"},
        ]
    },
    "google": {
        "name": "Google (Gemini)",
        "envVar": "GEMINI_API_KEY",
        "prefix": "gemini/",
        "models": [
            {"id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash", "label": "Gemini 1.5 Flash"},
            {"id": "gemini-2.0-flash-exp", "label": "Gemini 2.0 Flash"},
        ]
    },
    "cohere": {
        "name": "Cohere",
        "envVar": "COHERE_API_KEY",
        "prefix": "cohere/",
        "models": [
            {"id": "command-r-plus", "label": "Command R+"},
            {"id": "command-r", "label": "Command R"},
            {"id": "command", "label": "Command"},
        ]
    },
    "together_ai": {
        "name": "Together AI",
        "envVar": "TOGETHER_API_KEY",
        "prefix": "together_ai/",
        "models": [
            {"id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "label": "Llama 3.3 70B"},
            {"id": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "label": "Llama 3.1 405B"},
            {"id": "mistralai/Mixtral-8x22B-Instruct-v0.1", "label": "Mixtral 8x22B"},
        ]
    },
    "openrouter": {
        "name": "OpenRouter",
        "envVar": "OPENROUTER_API_KEY",
        "prefix": "openrouter/",
        "models": [
            {"id": "openai/gpt-4-turbo", "label": "GPT-4 Turbo"},
            {"id": "anthropic/claude-3.5-sonnet", "label": "Claude 3.5 Sonnet"},
            {"id": "google/gemini-pro-1.5", "label": "Gemini 1.5 Pro"},
            {"id": "meta-llama/llama-3.1-405b-instruct", "label": "Llama 3.1 405B"},
        ]
    },
    "deepseek": {
        "name": "DeepSeek",
        "envVar": "DEEPSEEK_API_KEY",
        "prefix": "deepseek/",
        "models": [
            {"id": "deepseek-chat", "label": "DeepSeek Chat"},
            {"id": "deepseek-coder", "label": "DeepSeek Coder"},
        ]
    },
    "cerebras": {
        "name": "Cerebras",
        "envVar": "CEREBRAS_API_KEY",
        "prefix": "cerebras/",
        "models": [
            {"id": "llama3.1-8b", "label": "Llama 3.1 8B"},
            {"id": "llama3.1-70b", "label": "Llama 3.1 70B"},
        ]
    },
}

# Cache
_cached_config: Optional[Dict[str, Any]] = None
_cached_accounts: Optional[List[Dict[str, Any]]] = None
_config_mtime: Optional[float] = None
_fernet: Optional[Any] = None


def _get_or_create_key() -> bytes:
    """Get or create the encryption key."""
    if SECRET_PATH.exists():
        return SECRET_PATH.read_bytes()

    key = Fernet.generate_key()
    SECRET_PATH.write_bytes(key)
    # Set restrictive permissions
    os.chmod(SECRET_PATH, 0o600)
    return key


def _get_fernet() -> Optional[Any]:
    """Get Fernet cipher for encryption/decryption."""
    global _fernet

    if not HAS_CRYPTO:
        return None

    if _fernet is None:
        key = _get_or_create_key()
        _fernet = Fernet(key)

    return _fernet


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key. Returns original if encryption unavailable."""
    fernet = _get_fernet()
    if not fernet:
        return api_key

    try:
        encrypted = fernet.encrypt(api_key.encode())
        return f"encrypted:{base64.urlsafe_b64encode(encrypted).decode()}"
    except Exception:
        return api_key


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key. Returns original if not encrypted or decryption fails."""
    if not encrypted_key.startswith("encrypted:"):
        return encrypted_key

    fernet = _get_fernet()
    if not fernet:
        return encrypted_key

    try:
        encrypted_data = base64.urlsafe_b64decode(encrypted_key[10:])
        return fernet.decrypt(encrypted_data).decode()
    except Exception:
        return encrypted_key


def generate_id() -> str:
    """Generate a unique preset ID: cfg-{timestamp}-{random6}"""
    random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"cfg-{int(time.time() * 1000)}-{random_chars}"


def get_env_var_name(provider: str, account_name: str) -> str:
    """
    Generate environment variable name for LiteLLM.
    Pattern: {PROVIDER}_{ACCOUNTNAME} (uppercase, spaces replaced with underscores)
    """
    provider_upper = provider.upper()
    account_upper = account_name.upper().replace(" ", "_").replace("-", "_")
    return f"{provider_upper}_{account_upper}"


def get_default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        "port": 11434,
        "account": "",
        "provider": "openai",
        "model": "gpt-4",
        "emulatedModelName": "",
        "emulatorActive": False,
        "lastConfig": None,
    }


def get_config() -> Dict[str, Any]:
    """Get current configuration with mtime-based cache invalidation."""
    global _cached_config, _config_mtime

    try:
        if _cached_config is not None:
            stats = CONFIG_PATH.stat()
            if _config_mtime is not None and stats.st_mtime == _config_mtime:
                return _cached_config
            _config_mtime = stats.st_mtime

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _cached_config = json.load(f)
        _config_mtime = CONFIG_PATH.stat().st_mtime
        return _cached_config
    except (FileNotFoundError, json.JSONDecodeError):
        return get_default_config()


def update_config(updates: Dict[str, Any]) -> bool:
    """Update configuration with new values."""
    global _cached_config, _config_mtime

    config = {**get_config(), **updates}
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        _cached_config = config
        _config_mtime = CONFIG_PATH.stat().st_mtime
        return True
    except Exception:
        return False


# =============================================================================
# Account Management with Encryption
# =============================================================================

def get_accounts() -> List[Dict[str, Any]]:
    """
    Get all saved accounts (with decrypted API keys).
    """
    global _cached_accounts

    try:
        if ACCOUNTS_PATH.exists():
            with open(ACCOUNTS_PATH, "r", encoding="utf-8") as f:
                accounts = json.load(f)
            if isinstance(accounts, list):
                # Decrypt API keys when loading
                for acc in accounts:
                    if "apiKey" in acc:
                        acc["apiKey"] = decrypt_api_key(acc["apiKey"])
                _cached_accounts = accounts
                return accounts
    except (json.JSONDecodeError, Exception):
        pass

    return []


def save_accounts(accounts: List[Dict[str, Any]]) -> bool:
    """Save accounts to file with encrypted API keys."""
    global _cached_accounts

    try:
        # Encrypt API keys before saving
        accounts_to_save = []
        for acc in accounts:
            acc_copy = acc.copy()
            if "apiKey" in acc_copy:
                acc_copy["apiKey"] = encrypt_api_key(acc_copy["apiKey"])
            accounts_to_save.append(acc_copy)

        with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
            json.dump(accounts_to_save, f, indent=2)
        _cached_accounts = accounts  # Keep decrypted version in cache
        return True
    except Exception:
        return False


def add_account(provider: str, account_name: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Add a new provider account.
    """
    accounts = get_accounts()

    # Check for duplicate (same provider + account name)
    for acc in accounts:
        if acc.get("provider") == provider and acc.get("accountName") == account_name:
            # Update existing account
            acc["apiKey"] = api_key
            acc["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if save_accounts(accounts):
                generate_litellm_config()  # Regenerate config
                return acc
            return None

    new_account = {
        "accountName": account_name,
        "provider": provider,
        "apiKey": api_key,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    accounts.append(new_account)

    if save_accounts(accounts):
        generate_litellm_config()  # Regenerate config
        return new_account
    return None


def remove_account(provider: str, account_name: str) -> bool:
    """Remove a provider account."""
    accounts = get_accounts()
    original_len = len(accounts)

    accounts = [
        acc for acc in accounts
        if not (acc.get("provider") == provider and acc.get("accountName") == account_name)
    ]

    if len(accounts) == original_len:
        return False

    result = save_accounts(accounts)
    if result:
        generate_litellm_config()  # Regenerate config
    return result


def get_account(provider: str, account_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific account by provider and name."""
    accounts = get_accounts()
    for acc in accounts:
        if acc.get("provider") == provider and acc.get("accountName") == account_name:
            return acc
    return None


def get_accounts_for_provider(provider: str) -> List[Dict[str, Any]]:
    """Get all accounts for a specific provider."""
    accounts = get_accounts()
    return [acc for acc in accounts if acc.get("provider") == provider]


def get_account_api_key(provider: str, account_name: str) -> Optional[str]:
    """Get the API key for a specific account."""
    account = get_account(provider, account_name)
    return account.get("apiKey") if account else None


# =============================================================================
# LiteLLM Config Generation
# =============================================================================

def generate_litellm_config() -> bool:
    """
    Generate LiteLLM config.yaml from saved accounts.

    Format:
    model_list:
      - model_name: claude-3-haiku  # What Pinokio sees
        litellm_params:
          model: anthropic/claude-3-haiku-20240307  # Real model
          api_key: os.environ/ANTHROPIC_PERSONAL  # Env var
    """
    accounts = get_accounts()
    config = get_config()

    # Start building YAML content
    yaml_lines = ["model_list:"]

    emulated_name = config.get("emulatedModelName", "")
    current_provider = config.get("provider", "")
    current_model = config.get("model", "")
    current_account = config.get("account", "")

    # If emulator is configured, add the emulated model
    if emulated_name and current_provider and current_model:
        provider_info = PROVIDER_REGISTRY.get(current_provider, {})
        prefix = provider_info.get("prefix", f"{current_provider}/")

        # Get the API key env var name
        if current_account:
            env_var = get_env_var_name(current_provider, current_account)
        else:
            env_var = provider_info.get("envVar", f"{current_provider.upper()}_API_KEY")

        # Build the real model string
        if current_provider == "openai":
            real_model = current_model
        else:
            real_model = f"{prefix}{current_model}"

        yaml_lines.append(f"  - model_name: {emulated_name}")
        yaml_lines.append("    litellm_params:")
        yaml_lines.append(f"      model: {real_model}")
        yaml_lines.append(f"      api_key: os.environ/{env_var}")
        yaml_lines.append("")

    # Add all provider models from accounts
    for acc in accounts:
        provider = acc.get("provider", "")
        account_name = acc.get("accountName", "")

        if not provider or not account_name:
            continue

        provider_info = PROVIDER_REGISTRY.get(provider, {})
        prefix = provider_info.get("prefix", f"{provider}/")
        env_var = get_env_var_name(provider, account_name)

        # Add each model from the provider
        for model in provider_info.get("models", []):
            model_id = model.get("id", "")
            if not model_id:
                continue

            # Build the real model string
            if provider == "openai":
                real_model = model_id
            else:
                real_model = f"{prefix}{model_id}"

            # Use model_id as the exposed name
            yaml_lines.append(f"  - model_name: {model_id}")
            yaml_lines.append("    litellm_params:")
            yaml_lines.append(f"      model: {real_model}")
            yaml_lines.append(f"      api_key: os.environ/{env_var}")
            yaml_lines.append("")

    # Write the config file
    try:
        with open(LITELLM_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(yaml_lines))
        return True
    except Exception:
        return False


def get_litellm_env_vars() -> Dict[str, str]:
    """
    Get environment variables needed for LiteLLM subprocess.
    Returns a dict of env var names to API key values.
    """
    accounts = get_accounts()
    env_vars = {}

    for acc in accounts:
        provider = acc.get("provider", "")
        account_name = acc.get("accountName", "")
        api_key = acc.get("apiKey", "")

        if provider and account_name and api_key:
            env_var = get_env_var_name(provider, account_name)
            env_vars[env_var] = api_key

    return env_vars


# =============================================================================
# Saved Configs (Presets)
# =============================================================================

def get_saved_configs() -> List[Dict[str, Any]]:
    """Get saved configuration presets."""
    try:
        if SAVED_CONFIGS_PATH.exists():
            with open(SAVED_CONFIGS_PATH, "r", encoding="utf-8") as f:
                configs = json.load(f)
            if isinstance(configs, list):
                return configs
    except (json.JSONDecodeError, Exception):
        pass
    return []


def save_saved_configs(configs: List[Dict[str, Any]]) -> bool:
    """Save configuration presets."""
    try:
        with open(SAVED_CONFIGS_PATH, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=2)
        return True
    except Exception:
        return False


def add_saved_config(name: str, provider: str, model: str,
                     emulated_model_name: str = "", account: str = "") -> Optional[Dict[str, Any]]:
    """Add a new saved configuration preset."""
    configs = get_saved_configs()
    new_config = {
        "id": generate_id(),
        "name": name,
        "account": account,
        "provider": provider,
        "model": model,
        "emulatedModelName": emulated_model_name,
    }
    configs.append(new_config)
    return new_config if save_saved_configs(configs) else None


def get_saved_config_by_id(config_id: str) -> Optional[Dict[str, Any]]:
    """Get a saved configuration preset by ID."""
    return next((c for c in get_saved_configs() if c.get("id") == config_id), None)


def update_saved_config(config_id: str, new_name: Optional[str], provider: Optional[str],
                        model: Optional[str], emulated_model_name: Optional[str] = None,
                        account: Optional[str] = None) -> bool:
    """Update an existing saved configuration preset."""
    configs = get_saved_configs()
    config = next((c for c in configs if c.get("id") == config_id), None)
    if config is None:
        return False

    if new_name:
        config["name"] = new_name
    if provider:
        config["provider"] = provider
    if model:
        config["model"] = model
    if emulated_model_name is not None:
        config["emulatedModelName"] = emulated_model_name
    if account is not None:
        config["account"] = account

    return save_saved_configs(configs)


def delete_saved_config(config_id: str) -> bool:
    """Delete a saved configuration preset."""
    configs = get_saved_configs()
    filtered = [c for c in configs if c.get("id") != config_id]
    if len(filtered) == len(configs):
        return False
    return save_saved_configs(filtered)


# =============================================================================
# Provider Utilities
# =============================================================================

def list_models(provider: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List available models, optionally filtered by provider.
    """
    models = []
    providers_to_check = [provider] if provider else list(PROVIDER_REGISTRY.keys())

    for prov in providers_to_check:
        if prov not in PROVIDER_REGISTRY:
            continue

        info = PROVIDER_REGISTRY[prov]
        for model in info["models"]:
            models.append({
                "id": model["id"],
                "label": model["label"],
                "provider": prov,
                "providerName": info["name"]
            })

    return models


def list_providers() -> List[Dict[str, Any]]:
    """List all providers with their account status."""
    accounts = get_accounts()

    # Group accounts by provider
    accounts_by_provider = {}
    for acc in accounts:
        prov = acc.get("provider", "")
        if prov not in accounts_by_provider:
            accounts_by_provider[prov] = []
        accounts_by_provider[prov].append(acc)

    providers = []
    for provider_id, info in PROVIDER_REGISTRY.items():
        provider_accounts = accounts_by_provider.get(provider_id, [])
        has_accounts = len(provider_accounts) > 0

        providers.append({
            "id": provider_id,
            "name": info["name"],
            "envVar": info["envVar"],
            "hasApiKey": has_accounts,
            "connected": has_accounts,
            "accountCount": len(provider_accounts),
            "models": info["models"]
        })

    return providers
