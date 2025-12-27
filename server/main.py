"""
Virtual Model Emulator - Main Server
Lightweight FastAPI server that serves the custom UI and manages LiteLLM proxy
"""

import asyncio
import os
import signal
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn

from .config import (
    get_config, update_config, get_accounts, add_account, remove_account,
    get_saved_configs, add_saved_config, update_saved_config, delete_saved_config,
    get_saved_config_by_id, generate_litellm_config,
    get_or_create_master_key, get_decrypted_api_key, CONFIG_DIR
)


# LiteLLM subprocess management
_litellm_process: Optional[subprocess.Popen] = None
_emulator_active: bool = False

# Models cache
_models_cache: Dict[str, Any] = {}

# Path to LiteLLM config
LITELLM_CONFIG_PATH = CONFIG_DIR / "config.yaml"

# Calculate paths
BASE_DIR = Path(__file__).parent.parent
PUBLIC_DIR = BASE_DIR / "public"


def clear_models_cache():
    """Clear the models cache."""
    global _models_cache
    _models_cache = {}


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def start_litellm_proxy(port: int = 11434) -> bool:
    """Start the LiteLLM proxy server as a subprocess."""
    global _litellm_process, _emulator_active
    
    if _litellm_process is not None and _litellm_process.poll() is None:
        # Already running
        return True
    
    # Check if litellm is installed
    try:
        import litellm
    except ImportError:
        print("[ERROR] litellm not installed", flush=True)
        return False
    
    # Check if port is in use
    if is_port_in_use(port):
        print(f"[ERROR] Port {port} is already in use", flush=True)
        return False
    
    # Generate the config file
    if not generate_litellm_config():
        print("[ERROR] Failed to generate LiteLLM config", flush=True)
        return False
    
    # Build environment with master key for LiteLLM
    env = os.environ.copy()
    env["LITELLM_MASTER_KEY"] = get_or_create_master_key()
    
    # Start LiteLLM proxy
    try:
        # Find litellm executable - prefer the one in the same directory as Python
        import shutil
        litellm_path = shutil.which("litellm")
        if not litellm_path:
            # Try to find it in the venv's bin/Scripts directory
            venv_litellm = Path(sys.executable).parent / "litellm"
            if venv_litellm.exists():
                litellm_path = str(venv_litellm)
            else:
                print("[ERROR] litellm executable not found", flush=True)
                return False

        cmd = [
            litellm_path,
            "--config", str(LITELLM_CONFIG_PATH),
            "--port", str(port),
            "--host", "127.0.0.1"
        ]
        
        print(f"[INFO] Starting LiteLLM proxy: {' '.join(cmd)}", flush=True)
        
        _litellm_process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Wait a moment to check if it started
        time.sleep(2)
        
        if _litellm_process.poll() is not None:
            # Process died
            if _litellm_process.stdout:
                output = _litellm_process.stdout.read()
                print(f"[ERROR] LiteLLM failed to start: {output}", flush=True)
            _litellm_process = None
            return False
        
        _emulator_active = True
        clear_models_cache()  # Clear cache when proxy starts
        print(f"[INFO] LiteLLM proxy started on port {port}", flush=True)
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to start LiteLLM: {e}", flush=True)
        _litellm_process = None
        return False


def stop_litellm_proxy() -> bool:
    """Stop the LiteLLM proxy subprocess."""
    global _litellm_process, _emulator_active
    
    if _litellm_process is None:
        _emulator_active = False
        return True
    
    try:
        _litellm_process.terminate()
        try:
            _litellm_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _litellm_process.kill()
            _litellm_process.wait()
        
        _litellm_process = None
        _emulator_active = False
        clear_models_cache()  # Clear cache when proxy stops
        print("[INFO] LiteLLM proxy stopped", flush=True)
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to stop LiteLLM: {e}", flush=True)
        return False


def is_emulator_running() -> bool:
    """Check if the LiteLLM proxy is running."""
    global _litellm_process, _emulator_active
    
    if _litellm_process is None:
        _emulator_active = False
        return False
    
    if _litellm_process.poll() is not None:
        # Process has exited
        _litellm_process = None
        _emulator_active = False
        return False
    
    return _emulator_active


async def fetch_litellm_models() -> List[Dict[str, Any]]:
    """Fetch models from LiteLLM /v1/models endpoint."""
    try:
        config = get_config()
        emulator_port = config.get("emulatorPort", 11434)
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{emulator_port}/v1/models", timeout=5.0)
            if response.status_code == 200:
                return response.json().get("data", [])
    except Exception:
        pass
    return []


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    config = get_config()
    management_port = config.get("managementPort", 8765)
    emulator_port = config.get("emulatorPort", 11434)

    print(f"[INFO] Virtual Model Emulator Management UI on http://localhost:{management_port}", flush=True)
    print(f"PINOKIO_STARTUP: http://localhost:{management_port}/config.html", flush=True)
    print(f"[INFO] Connect UI: http://localhost:{management_port}/connect.html", flush=True)
    print(f"[INFO] LiteLLM API will be available on: http://localhost:{emulator_port}/v1/chat/completions", flush=True)

    # Ensure config directory exists
    CONFIG_DIR.mkdir(exist_ok=True)

    yield

    # Cleanup on shutdown
    stop_litellm_proxy()
    print("[INFO] Shutting down...", flush=True)


# Create FastAPI app
app = FastAPI(
    title="Virtual Model Emulator",
    description="OpenAI-compatible endpoint using LiteLLM proxy server",
    version="2.0.0",
    lifespan=lifespan
)


# =============================================================================
# Config State for UI
# =============================================================================

@app.get("/config/state")
async def config_state():
    """Get current configuration state for the UI."""
    config = get_config()
    accounts = get_accounts()
    
    # Build safe accounts list (without encrypted API keys)
    safe_accounts = [
        {
            "accountName": acc.get("accountName", ""),
            "provider": acc.get("provider", ""),
            "createdAt": acc.get("createdAt", "")
        }
        for acc in accounts
    ]
    
    # Get unique providers from accounts
    providers_set = set()
    for acc in accounts:
        if acc.get("provider"):
            providers_set.add(acc.get("provider"))
    
    providers = [{"id": p, "name": p.title(), "hasApiKey": True} for p in sorted(providers_set)]
    
    return JSONResponse(content={
        "config": config,
        "presets": get_saved_configs(),
        "models": [],  # Models fetched on demand from LiteLLM
        "providers": providers,
        "accounts": safe_accounts,
        "emulatorActive": is_emulator_running(),
    })


@app.post("/config/save")
async def config_save(request: Request):
    """Save configuration."""
    body = await request.json()
    updates = {}
    
    if "account" in body:
        updates["account"] = body["account"]
    if "provider" in body:
        updates["provider"] = body["provider"]
    if "model" in body:
        updates["model"] = body["model"]
    if "emulatedModelName" in body:
        updates["emulatedModelName"] = body["emulatedModelName"]
    if "port" in body:
        updates["port"] = int(body["port"])
    
    success = update_config(updates)
    if success:
        # Regenerate LiteLLM config
        generate_litellm_config()
        return JSONResponse(content={"success": True, "config": get_config()})
    else:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to save configuration"}
        )


@app.post("/config/savePreset")
async def config_save_preset(request: Request):
    """Save or update a configuration preset."""
    body = await request.json()
    
    name = body.get("name", "").strip()
    preset_id = body.get("id")
    provider = body.get("provider")
    model = body.get("model")
    emulated_model_name = body.get("emulatedModelName", "")
    account = body.get("account", "")
    
    if not name:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Name is required"}
        )
    
    if not provider:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Provider is required"}
        )
    
    if not model:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Model is required"}
        )
    
    if preset_id:
        # Update existing preset
        if not get_saved_config_by_id(preset_id):
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Preset not found"}
            )
        
        ok = update_saved_config(preset_id, name, provider, model, emulated_model_name, account)
        if ok:
            updated = get_saved_config_by_id(preset_id)
            return JSONResponse(content={"success": True, "preset": updated})
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to update preset"}
            )
    else:
        # Create new preset
        preset = add_saved_config(name, provider, model, emulated_model_name, account)
        if preset:
            return JSONResponse(content={"success": True, "preset": preset})
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to save preset"}
            )


# =============================================================================
# Provider Account Management
# =============================================================================

@app.get("/providers")
async def get_providers():
    """List all providers with their connection status."""
    accounts = get_accounts()
    
    # Get unique providers from accounts
    providers_set = set()
    for acc in accounts:
        if acc.get("provider"):
            providers_set.add(acc.get("provider"))
    
    providers = [{"id": p, "name": p.title(), "hasApiKey": True} for p in sorted(providers_set)]
    return JSONResponse(content={"providers": providers})


@app.get("/providers/accounts")
async def get_provider_accounts():
    """List all saved accounts (without exposing encrypted API keys)."""
    accounts = get_accounts()
    safe_accounts = [
        {
            "accountName": acc.get("accountName", ""),
            "provider": acc.get("provider", ""),
            "createdAt": acc.get("createdAt", ""),
            "hasApiKey": bool(acc.get("encryptedApiKey"))
        }
        for acc in accounts
    ]
    return JSONResponse(content=safe_accounts)


@app.post("/providers/connect")
async def connect_provider(request: Request):
    """Save API key with account name for a provider."""
    body = await request.json()
    
    provider = body.get("provider", "").strip()
    account_name = body.get("accountName", "").strip()
    api_key = body.get("apiKey", "").strip()
    
    if not provider:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Provider is required"}
        )
    
    if not account_name:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Account name is required"}
        )
    
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "API key is required"}
        )
    
    # Add the account (this encrypts the key and stores it)
    account = add_account(provider, account_name, api_key)
    if account:
        clear_models_cache()  # Clear cache when provider connected
        return JSONResponse(content={
            "success": True,
            "account": {
                "accountName": account["accountName"],
                "provider": account["provider"],
                "createdAt": account.get("createdAt", "")
            }
        })
    else:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to save account"}
        )


@app.post("/providers/disconnect")
async def disconnect_provider(request: Request):
    """Remove a specific account."""
    body = await request.json()
    
    provider = body.get("provider", "").strip()
    account_name = body.get("accountName", "").strip()
    
    if not provider:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Provider is required"}
        )
    
    if not account_name:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Account name is required"}
        )
    
    if remove_account(provider, account_name):
        clear_models_cache()  # Clear cache when provider disconnected
        return JSONResponse(content={"success": True})
    else:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Account not found"}
        )


@app.get("/providers/models")
async def get_provider_models(provider: Optional[str] = Query(None)):
    """Get models for a specific provider from LiteLLM."""
    models = await fetch_litellm_models()
    if provider:
        models = [m for m in models if provider in m.get("id", "")]
    return JSONResponse(content={"models": models})


@app.post("/providers/test")
async def test_provider_connection(request: Request):
    """Test API key by making a request to the provider."""
    body = await request.json()

    provider = body.get("provider", "").strip()
    account_name = body.get("accountName", "").strip()

    if not provider:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Provider is required"}
        )

    if not account_name:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Account name is required"}
        )

    # Get the decrypted API key
    api_key = get_decrypted_api_key(provider, account_name)
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Could not retrieve API key for this account"}
        )

    # Provider-specific test endpoints
    test_configs = {
        "openai": {
            "url": "https://api.openai.com/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        },
        "anthropic": {
            "url": "https://api.anthropic.com/v1/messages",
            "headers": {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            "method": "POST",
            "body": {"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "Hi"}]}
        },
        "groq": {
            "url": "https://api.groq.com/openai/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        },
        "mistral": {
            "url": "https://api.mistral.ai/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        },
        "google": {
            "url": f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
            "headers": {}
        },
        "cohere": {
            "url": "https://api.cohere.ai/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        },
        "together_ai": {
            "url": "https://api.together.xyz/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        },
        "openrouter": {
            "url": "https://openrouter.ai/api/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        },
        "deepseek": {
            "url": "https://api.deepseek.com/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        },
        "cerebras": {
            "url": "https://api.cerebras.ai/v1/models",
            "headers": {"Authorization": f"Bearer {api_key}"}
        }
    }

    config = test_configs.get(provider)
    if not config:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": f"Unknown provider: {provider}"}
        )

    try:
        async with httpx.AsyncClient() as client:
            if config.get("method") == "POST":
                response = await client.post(
                    config["url"],
                    headers=config["headers"],
                    json=config.get("body", {}),
                    timeout=10.0
                )
            else:
                response = await client.get(
                    config["url"],
                    headers=config["headers"],
                    timeout=10.0
                )

            if response.status_code == 200 or response.status_code == 201:
                return JSONResponse(content={
                    "success": True,
                    "message": f"Successfully connected to {provider.title()}"
                })
            elif response.status_code == 401:
                return JSONResponse(content={
                    "success": False,
                    "error": "Invalid API key"
                })
            else:
                return JSONResponse(content={
                    "success": False,
                    "error": f"Provider returned status {response.status_code}"
                })

    except httpx.TimeoutException:
        return JSONResponse(content={
            "success": False,
            "error": "Connection timed out"
        })
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": f"Connection failed: {str(e)}"
        })


# =============================================================================
# Models
# =============================================================================

@app.get("/models")
async def get_models_endpoint(
    provider: Optional[str] = Query(None),
    force: bool = Query(False)
):
    """Get available models with caching."""
    global _models_cache
    
    cache_key = provider or "all"
    
    if not force and cache_key in _models_cache:
        return JSONResponse(content={"models": _models_cache[cache_key]})
    
    models = await fetch_litellm_models()
    
    if provider:
        models = [m for m in models if provider in m.get("id", "")]
    
    _models_cache[cache_key] = models
    return JSONResponse(content={"models": models})


# =============================================================================
# Emulator Control
# =============================================================================

@app.post("/emulator/start")
async def emulator_start(request: Request):
    """Start the emulator with specified configuration."""
    body = await request.json()
    
    account = body.get("account", "")
    provider = body.get("provider")
    model = body.get("model")
    emulated_model_name = body.get("emulatedModelName", "")
    
    if not provider:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Provider is required"}
        )
    
    if not model:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Model is required"}
        )
    
    # Save the configuration
    update_config({
        "account": account,
        "provider": provider,
        "model": model,
        "emulatedModelName": emulated_model_name,
        "emulatorActive": True,
        "lastConfig": {
            "account": account,
            "provider": provider,
            "model": model,
            "emulatedModelName": emulated_model_name
        }
    })
    
    # Regenerate config and start proxy
    generate_litellm_config()

    config = get_config()
    emulator_port = config.get("emulatorPort", 11434)

    if start_litellm_proxy(emulator_port):
        emulated_info = f" (emulating '{emulated_model_name}')" if emulated_model_name else ""
        account_info = f" using account '{account}'" if account else ""
        print(f"[INFO] Emulator started: {provider}/{model}{emulated_info}{account_info}", flush=True)
        
        return JSONResponse(content={
            "success": True,
            "config": {
                "account": account,
                "provider": provider,
                "model": model,
                "emulatedModelName": emulated_model_name
            }
        })
    else:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to start LiteLLM proxy"}
        )


@app.post("/emulator/stop")
async def emulator_stop():
    """Stop the emulator."""
    update_config({"emulatorActive": False})
    
    if stop_litellm_proxy():
        print("[INFO] Emulator stopped", flush=True)
        return JSONResponse(content={"success": True})
    else:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to stop emulator"}
        )


@app.get("/emulator/status")
async def emulator_status():
    """Get detailed emulator status."""
    config = get_config()
    provider = config.get("provider", "openai")
    running = is_emulator_running()
    
    return JSONResponse(content={
        "emulatorRunning": running,
        "providerOnline": running,  # If proxy is running, provider is accessible
        "currentConfig": {
            "account": config.get("account", ""),
            "provider": provider,
            "providerName": provider.title(),
            "model": config.get("model", ""),
            "emulatedModelName": config.get("emulatedModelName", "")
        },
        "lastConfig": config.get("lastConfig")
    })


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Check if the emulator/proxy is running."""
    running = is_emulator_running()
    config = get_config()
    provider = config.get("provider", "openai")
    
    return JSONResponse(content={
        "online": running,
        "provider": provider,
        "message": f"{provider.title()} proxy is running" if running else f"{provider.title()} proxy is not running"
    })


# =============================================================================
# Shutdown
# =============================================================================

@app.post("/shutdown")
async def shutdown():
    """Graceful shutdown."""
    print("[INFO] Shutdown requested from UI", flush=True)
    
    # Stop the proxy first
    stop_litellm_proxy()
    
    # Schedule shutdown after response is sent
    async def do_shutdown():
        await asyncio.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)
    
    asyncio.create_task(do_shutdown())
    
    return JSONResponse(content={"success": True, "message": "Shutting down..."})


# =============================================================================
# Root and Static Files
# =============================================================================

@app.get("/")
async def root():
    """Redirect to config UI."""
    return RedirectResponse(url="/config.html")


# Mount static files (must be after all routes)
app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")


def main():
    """Main entry point."""
    # Get port from config
    config = get_config()
    management_port = config.get("managementPort", 8765)
    emulator_port = config.get("emulatorPort", 11434)

    print(f"[INFO] Starting Virtual Model Emulator")
    print(f"[INFO] Management UI: http://localhost:{management_port}/config.html")
    print(f"[INFO] Connect UI: http://localhost:{management_port}/connect.html")
    print(f"[INFO] LiteLLM API (when started): http://localhost:{emulator_port}/v1/chat/completions")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=management_port,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    main()
