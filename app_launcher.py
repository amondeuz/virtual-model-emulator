"""
Virtual Model Emulator - Simplified Launcher
Starts only the API server (uses LiteLLM SDK directly, no proxy or database needed).
"""
import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

services = {}  # {name: process_object}
stop_event = threading.Event()

# Default port
API_SERVER_PORT = int(os.environ.get('API_SERVER_PORT', 8775))


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    print(f'\n[INFO] Received signal {sig} - shutting down', flush=True)
    stop_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def setup_environment():
    """Prepare environment for all subprocesses."""
    env = os.environ.copy()

    # Critical Windows encoding settings
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    env['PYTHONLEGACYWINDOWSSTDIO'] = '0'

    # Load .env if available (for API_SERVER_PORT, etc.)
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from env_loader import load_env
        env_vars = load_env()
        env.update(env_vars)
    except Exception as e:
        print(f'[WARN] Failed to load .env: {e}', flush=True)

    return env


def check_server_ready(port=None):
    """Check if API server is responding."""
    import urllib.request
    port = port or API_SERVER_PORT
    try:
        response = urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=2)
        return response.getcode() == 200
    except Exception:
        return False


def wait_for_service_ready(service_name, check_func, timeout=30):
    """Wait for a service to be ready using a check function."""
    print(f'[INFO] Waiting for {service_name} to be ready...', flush=True)

    start = time.time()
    while time.time() - start < timeout:
        if stop_event.is_set():
            return False

        try:
            if check_func():
                print(f'[OK] {service_name} is ready', flush=True)
                return True
        except Exception:
            pass

        time.sleep(1)

    print(f'[ERROR] {service_name} not ready after {timeout}s', flush=True)
    return False


def stream_output_in_background(process, service_name):
    """Read process output line by line in background thread (prevents deadlock)."""
    def read_output():
        try:
            for line in iter(process.stdout.readline, ''):
                if stop_event.is_set():
                    break
                if line.strip():
                    print(f'[{service_name}] {line.rstrip()}', flush=True)
        except (ValueError, OSError):
            pass
        except Exception as e:
            print(f'[WARN] Output stream error for {service_name}: {e}', flush=True)

    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()


def start_service(script_name, service_name, env):
    """Start a service subprocess."""
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f'[ERROR] {script_name} not found', flush=True)
        return None

    print(f'[INFO] Starting {service_name}...', flush=True)

    creation_flags = 0
    if sys.platform == 'win32':
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

    try:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creation_flags
        )

        stream_output_in_background(process, service_name)

        # Give service time to fail fast
        time.sleep(2)
        if process.poll() is not None:
            print(f'[ERROR] {service_name} exited immediately', flush=True)
            return None

        print(f'[OK] {service_name} started', flush=True)
        services[service_name] = process
        return process

    except Exception as e:
        print(f'[ERROR] Failed to start {service_name}: {e}', flush=True)
        return None


def monitor_services():
    """Monitor all services continuously."""
    while not stop_event.is_set():
        for service_name, process in list(services.items()):
            if process and process.poll() is not None:
                print(f'[ERROR] {service_name} exited', flush=True)

        time.sleep(5)


def shutdown_services():
    """Gracefully shutdown all services."""
    print('[INFO] Shutting down services...', flush=True)

    for service_name in reversed(list(services.keys())):
        process = services.get(service_name)
        if process and process.poll() is None:
            print(f'[INFO] Stopping {service_name}...', flush=True)
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    print('[INFO] Virtual Model Emulator v2.2.2 - SDK Mode (No Proxy)', flush=True)
    print('[INFO] Architecture: API Server → LiteLLM SDK → Provider APIs', flush=True)

    env = setup_environment()

    # Start only the API server (it uses LiteLLM SDK directly)
    if not start_service('server.py', 'API Server', env):
        print('[ERROR] API Server failed to start', flush=True)
        shutdown_services()
        sys.exit(1)

    # Verify service is ready
    print('\n[INFO] Verifying service readiness...', flush=True)

    if not wait_for_service_ready('API Server', check_server_ready, 15):
        print('[ERROR] API Server is not responding', flush=True)
        shutdown_services()
        sys.exit(1)

    print('\n' + '=' * 50, flush=True)
    print('[OK] All services started and verified', flush=True)
    print('=' * 50, flush=True)
    print(f'[INFO] Web UI: http://localhost:{API_SERVER_PORT}/config.html', flush=True)
    print('[INFO] Emulator uses LiteLLM SDK directly - no proxy needed!', flush=True)

    # Start monitoring
    monitor_thread = threading.Thread(target=monitor_services, daemon=True)
    monitor_thread.start()

    # Wait for shutdown
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n[INFO] Keyboard interrupt', flush=True)
    finally:
        shutdown_services()
        print('[INFO] Launcher exiting', flush=True)


if __name__ == '__main__':
    main()
