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


def stream_output_in_background(process, service_name):
    """Read process output in background thread (prevents deadlock)."""
    def read_output():
        try:
            while not stop_event.is_set():
                if process.poll() is not None:
                    # Process exited, read remaining
                    try:
                        remaining = process.stdout.read()
                        if remaining:
                            for line in remaining.splitlines():
                                if line.strip():
                                    print(f'[{service_name}] {line}', flush=True)
                    except:
                        pass
                    break

                # Read available data (non-blocking)
                try:
                    chunk = process.stdout.read(1024)
                    if chunk:
                        for line in chunk.splitlines():
                            if line.strip():
                                print(f'[{service_name}] {line}', flush=True)
                    else:
                        time.sleep(0.1)
                except (BlockingIOError, ValueError):
                    time.sleep(0.1)
                except Exception:
                    break
        finally:
            pass

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
    print('[INFO] Virtual Model Emulator v2.1.2 - Unified Launcher', flush=True)

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

    print('[OK] All services started successfully', flush=True)

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
