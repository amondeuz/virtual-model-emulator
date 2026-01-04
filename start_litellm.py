"""Start and monitor LiteLLM proxy server."""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

shutdown_requested = False


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    print(f'\n[INFO] Received signal {sig}', flush=True)
    shutdown_requested = True


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print('[INFO] Preparing LiteLLM environment...', flush=True)

    # Mock litellm_enterprise modules IN THIS PROCESS (before subprocess)
    import types
    sys.modules['litellm_enterprise'] = types.ModuleType('litellm_enterprise')
    sys.modules['litellm_enterprise.proxy'] = types.ModuleType('proxy')
    sys.modules['litellm_enterprise.proxy.common_utils'] = types.ModuleType('common_utils')
    sys.modules['litellm_enterprise.proxy.common_utils'].check_responses_cost = None
    sys.modules['litellm_enterprise.proxy.common_utils'].check_batch_cost = None
    print('[OK] Enterprise modules mocked', flush=True)

    # Load configuration
    try:
        from env_loader import load_env, get_database_url, update_database_url_port
        env_vars = load_env()
        database_url = get_database_url(env_vars)
    except Exception as e:
        print(f'[ERROR] Failed to load configuration: {e}', flush=True)
        sys.exit(1)

    # Get PostgreSQL port from database_url
    from urllib.parse import urlparse
    try:
        parsed = urlparse(database_url)
        pg_port = parsed.port or 5450
        print(f'[INFO] PostgreSQL port from URL: {pg_port}', flush=True)
    except Exception:
        pg_port = 5450

    # Prepare environment
    process_env = os.environ.copy()
    process_env['DATABASE_URL'] = database_url
    process_env['PYTHONIOENCODING'] = 'utf-8'
    process_env['PYTHONUTF8'] = '1'

    # LiteLLM configuration
    litellm_port = 11435
    config_file = Path(__file__).parent / 'config.yaml'

    if not config_file.exists():
        print(f'[ERROR] config.yaml not found', flush=True)
        sys.exit(1)

    print('[INFO] Starting LiteLLM proxy...', flush=True)

    # Windows process isolation
    creation_flags = 0
    if sys.platform == 'win32':
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

    try:
        process = subprocess.Popen(
            [
                sys.executable, '-m', 'litellm',
                '--config', str(config_file),
                '--port', str(litellm_port),
                '--host', '127.0.0.1'
            ],
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creation_flags
        )

        print(f'[OK] LiteLLM process started (PID {process.pid})', flush=True)

    except Exception as e:
        print(f'[ERROR] Failed to start LiteLLM: {e}', flush=True)
        sys.exit(1)

    # Save PID
    try:
        with open('litellm_server.pid', 'w') as f:
            f.write(str(process.pid))
    except Exception:
        pass

    print('[OK] Uvicorn running', flush=True)
    print('[INFO] Monitoring LiteLLM process...', flush=True)

    # Monitor process
    try:
        while not shutdown_requested:
            exit_code = process.poll()
            if exit_code is not None:
                print(f'[ERROR] LiteLLM exited with code {exit_code}', flush=True)
                break

            # Read available output
            try:
                chunk = process.stdout.read(1024)
                if chunk:
                    for line in chunk.splitlines():
                        if line.strip():
                            print(f'[LiteLLM] {line}', flush=True)
            except Exception:
                pass

            time.sleep(1)

    except KeyboardInterrupt:
        print('\n[INFO] Shutdown signal received', flush=True)
    except Exception as e:
        print(f'[ERROR] Monitoring error: {e}', flush=True)
    finally:
        # Clean shutdown
        if process.poll() is None:
            print('[INFO] Stopping LiteLLM...', flush=True)
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        # Clean up PID file
        try:
            if os.path.exists('litellm_server.pid'):
                os.remove('litellm_server.pid')
        except Exception:
            pass

        print('[INFO] LiteLLM service exiting', flush=True)


if __name__ == '__main__':
    main()
