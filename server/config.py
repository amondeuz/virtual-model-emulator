"""
Configuration manager for the Virtual Model Emulator
Uses LiteLLM's native encryption for API keys
"""

import base64
import json
import os
import random
import string
import time
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
PUBLIC_DIR = BASE_DIR / "public"
CONFIG_PATH = CONFIG_DIR / "default.json"
ACCOUNTS_PATH = CONFIG_DIR / "accounts.json"
LITELLM_CONFIG_PATH = CONFIG_DIR / "config.yaml"
SAVED_CONFIGS_PATH = CONFIG_DIR / "saved-configs.json"
MASTER_KEY_PATH = CONFIG_DIR / ".master_key"

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Cache
_cached_config: Optional[Dict[str, Any]] = None
_cached_accounts: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# Master Key Management (For LiteLLM Encryption)
# =============================================================================

def get_or_create_master_key() -> str:
    """Get or create a master key for LiteLLM encryption."""
    if MASTER_KEY_PATH.exists():
        return MASTER_KEY_PATH.read_text().strip()
    
    # Generate new 32-byte base64-encoded master key
    import secrets
    master_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    MASTER_KEY_PATH.write_text(master_key)
    MASTER_KEY_PATH.chmod(0o600)  # Restrictive permissions
    return master_key


def encrypt_with_litellm(api_key: str, master_key: str) -> str:
    """Encrypt an API key using LiteLLM's encryption."""
    try:
        # Try using LiteLLM Python library
        from litellm import encrypt_key
        return encrypt_key(api_key, master_key)
    except (ImportError, AttributeError):
        # Fallback to CLI
        try:
            result = subprocess.run(
                ["python", "-m", "litellm", "--encrypt", f"--key={master_key}"],
                input=api_key,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Final fallback: simple base64 encoding (not secure, but functional)
        return f"base64:{base64.b64encode(api_key.encode()).decode()}"


def decrypt_with_litellm(encrypted_key: str, master_key: str) -> Optional[str]:
    """Decrypt an API key using LiteLLM's master key."""
    if encrypted_key.startswith("base64:"):
        # Handle our fallback encoding
        try:
            return base64.b64decode(encrypted_key[7:]).decode()
        except:
            return None
    return None  # LiteLLM handles decryption internally


# =============================================================================
# Account Management (Stores encrypted keys for LiteLLM)
# =============================================================================

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
    """Get current configuration."""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return get_default_config()


def update_config(updates: Dict[str, Any]) -> bool:
    """Update configuration with new values."""
    config = {**get_config(), **updates}
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def get_accounts() -> List[Dict[str, Any]]:
    """Get all saved accounts with encrypted API keys."""
    try:
        if ACCOUNTS_PATH.exists():
            with open(ACCOUNTS_PATH, "r", encoding="utf-8") as f:
                accounts = json.load(f)
                if isinstance(accounts, list):
                    return accounts
    except:
        pass
    return []


def save_accounts(accounts: List[Dict[str, Any]]) -> bool:
    """Save accounts to file."""
    try:
        with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
            json.dump(accounts, f, indent=2)
        return True
    except Exception:
        return False


def add_account(provider: str, account_name: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Add a new provider account with encrypted API key."""
    accounts = get_accounts()
    
    # Encrypt the API key with LiteLLM's master key
    master_key = get_or_create_master_key()
    encrypted_key = encrypt_with_litellm(api_key, master_key)
    
    # Check for existing account
    for i, acc in enumerate(accounts):
        if acc.get("provider") == provider and acc.get("accountName") == account_name:
            accounts[i] = {
                "accountName": account_name,
                "provider": provider,
                "encryptedApiKey": encrypted_key,
                "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            if save_accounts(accounts):
                return accounts[i]
            return None
    
    # Add new account
    new_account = {
        "accountName": account_name,
        "provider": provider,
        "encryptedApiKey": encrypted_key,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    accounts.append(new_account)
    return new_account if save_accounts(accounts) else None


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
    
    return save_accounts(accounts)


def get_account(provider: str, account_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific account by provider and name."""
    accounts = get_accounts()
    for acc in accounts:
        if acc.get("provider") == provider and acc.get("accountName") == account_name:
            return acc
    return None


def get_encrypted_api_key(provider: str, account_name: str) -> Optional[str]:
    """Get the encrypted API key for a specific account."""
    account = get_account(provider, account_name)
    return account.get("encryptedApiKey") if account else None


# =============================================================================
# LiteLLM Config Generation
# =============================================================================

def get_provider_prefix(provider: str) -> str:
    """Get the LiteLLM prefix for a provider."""
    if provider == "openai":
        return ""
    if provider == "google":
        return "gemini/"
    return f"{provider}/"


def generate_litellm_config() -> bool:
    """Generate LiteLLM config.yaml with encrypted API keys."""
    config = get_config()
    
    if not config.get("provider") or not config.get("model"):
        return False
    
    # Get encrypted API key for the selected account
    encrypted_key = None
    if config.get("account"):
        encrypted_key = get_encrypted_api_key(config["provider"], config["account"])
    
    if not encrypted_key:
        return False
    
    # Build the config.yaml
    yaml_lines = [
        "model_list:",
        f"  - model_name: {config.get('emulatedModelName', 'default')}",
        "    litellm_params:",
        f"      model: {get_provider_prefix(config['provider'])}{config['model']}",
        f"      api_key: {encrypted_key}",
        "",
        "general_settings:",
        "  master_key: os.environ/LITELLM_MASTER_KEY",
        "  drop_params: true",
        "  set_verbose: true",
        "",
        "litellm_settings:",
        "  drop_params: true",
        "  set_verbose: true",
    ]
    
    # Write the config file
    try:
        with open(LITELLM_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(yaml_lines))
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write LiteLLM config: {e}")
        return False


# =============================================================================
# Saved Configs (Presets)
# =============================================================================

def generate_id() -> str:
    """Generate a unique preset ID."""
    random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"cfg-{int(time.time() * 1000)}-{random_chars}"


def get_saved_configs() -> List[Dict[str, Any]]:
    """Get saved configuration presets."""
    try:
        if SAVED_CONFIGS_PATH.exists():
            with open(SAVED_CONFIGS_PATH, "r", encoding="utf-8") as f:
                configs = json.load(f)
                if isinstance(configs, list):
                    return configs
    except:
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