"""
Virtual Model Emulator - Unified Service Launcher
Starts all services under a single parent process that Pinokio monitors.
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

# Default ports
PG_PORT = int(os.environ.get('PG_PORT', 5450))
LITELLM_PORT = int(os.environ.get('LITELLM_PORT', 11435))
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

    # Load .env if available
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from env_loader import load_env
        env_vars = load_env()
        env.update(env_vars)
    except Exception as e:
        print(f'[WARN] Failed to load .env: {e}', flush=True)

    return env


def check_postgres_ready(port=None):
    """Check if PostgreSQL is accepting database connections."""
    port = port or PG_PORT
    try:
        # Try to connect with psycopg2 if available, fall back to socket
        try:
            import psycopg2
            conn = psycopg2.connect(
                f"host=127.0.0.1 port={port} user=postgres connect_timeout=2"
            )
            conn.close()
            return True
        except ImportError:
            # Fallback: just check if port is listening
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
    except Exception:
        return False


def check_litellm_ready(port=None):
    """Check if LiteLLM /health endpoint responds."""
    import urllib.request
    port = port or LITELLM_PORT
    try:
        response = urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2)
        return response.getcode() == 200
    except Exception:
        return False


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
    """Wait for a service to be ready using a check function.

    Args:
        service_name: Name of the service (for logging)
        check_func: Function that returns True if service is ready
        timeout: Maximum seconds to wait

    Returns:
        bool: True if service became ready, False if timeout
    """
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
            # Use iter() for clean line-by-line reading
            for line in iter(process.stdout.readline, ''):
                if stop_event.is_set():
                    break
                if line.strip():  # Skip empty lines
                    print(f'[{service_name}] {line.rstrip()}', flush=True)
        except (ValueError, OSError):
            # Process closed stdout
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
        time.sleep(3)
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
    print('[INFO] Virtual Model Emulator v2.1.5 - Unified Launcher', flush=True)

    env = setup_environment()

    # Start services in order
    if not start_service('start_postgres.py', 'PostgreSQL', env):
        shutdown_services()
        sys.exit(1)

    time.sleep(2)

    if not start_service('start_litellm.py', 'LiteLLM', env):
        shutdown_services()
        sys.exit(1)

    time.sleep(2)

    if not start_service('server.py', 'API Server', env):
        print('[WARN] API Server failed', flush=True)

    # Verify all services are actually ready
    print('\n[INFO] Verifying service readiness...', flush=True)

    all_ready = True
    service_checks = [
        ('PostgreSQL', check_postgres_ready, 30),
        ('LiteLLM', check_litellm_ready, 45),  # LiteLLM takes longer to start
        ('API Server', check_server_ready, 15)
    ]

    for service_name, check_func, timeout in service_checks:
        if not wait_for_service_ready(service_name, check_func, timeout):
            all_ready = False
            print(f'[WARN] {service_name} is not responding', flush=True)

    if all_ready:
        print('\n' + '=' * 50, flush=True)
        print('[OK] All services started and verified', flush=True)
        print('=' * 50, flush=True)
    else:
        print('\n[WARN] Some services may not be fully ready', flush=True)
        print('[INFO] The application will continue running', flush=True)

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
