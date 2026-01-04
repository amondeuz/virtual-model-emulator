"""Start and monitor LiteLLM proxy server."""
import os
import subprocess
import sys
import time
import signal
import socket
import types
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from env_loader import load_env, get_database_url
from postgres_manager import PostgreSQLManager

# Global shutdown flag
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    print(f'\n[INFO] Received signal {sig}', flush=True)
    shutdown_requested = True


def get_postgres_port_from_database_url(database_url):
    """Extract PostgreSQL port from DATABASE_URL safely using URL parser."""
    try:
        parsed = urlparse(database_url)
        if parsed.port:
            return parsed.port
        return 5432  # Default PostgreSQL port
    except Exception as e:
        print(f'[WARN] Failed to parse port from DATABASE_URL: {e}', flush=True)
        return 5432


def is_litellm_ready(host='127.0.0.1', port=None, timeout=30):
    """Check if LiteLLM is listening on the port.

    Args:
        host: LiteLLM host
        port: LiteLLM port (as string or int)
        timeout: Maximum seconds to wait

    Returns:
        bool: True if LiteLLM is responding to connections
    """
    if port is None:
        return False

    port = int(port)
    start = time.time()

    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                print(f'[OK] LiteLLM is listening on {host}:{port}', flush=True)
                return True
        except Exception:
            pass

        time.sleep(0.5)

    return False


def generate_prisma_client():
    """Generate Prisma client from litellm_proxy_extras package directory.

    Returns:
        bool: True if successful, False if failed
    """
    print('[INFO] Generating Prisma client...', flush=True)

    try:
        import litellm_proxy_extras
        package_dir = litellm_proxy_extras.__path__[0]
        print(f'[INFO] Found litellm_proxy_extras at: {package_dir}', flush=True)
    except ImportError:
        print('[ERROR] litellm_proxy_extras not found', flush=True)
        return False
    except Exception as e:
        print(f'[ERROR] Failed to find litellm_proxy_extras: {e}', flush=True)
        return False

    try:
        print('[INFO] Running prisma generate...', flush=True)
        result = subprocess.run(
            [sys.executable, '-m', 'prisma', 'generate'],
            cwd=package_dir,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print('[OK] Prisma client generated successfully', flush=True)
            return True
        else:
            print(f'[ERROR] prisma generate failed: {result.stderr[:500]}', flush=True)
            return False

    except subprocess.TimeoutExpired:
        print('[ERROR] prisma generate timed out (>60 seconds)', flush=True)
        return False
    except Exception as e:
        print(f'[ERROR] prisma generate error: {e}', flush=True)
        return False


def mock_enterprise_modules():
    """Mock litellm_enterprise modules in current process.

    CRITICAL: This must be done BEFORE starting the subprocess.
    The mocked modules will be inherited by the subprocess.
    """
    print('[INFO] Mocking enterprise modules...', flush=True)

    # Create dummy enterprise module
    dummy_module = types.ModuleType("litellm_enterprise")
    dummy_module.__path__ = []
    sys.modules["litellm_enterprise"] = dummy_module

    # Create dummy proxy submodule
    dummy_proxy = types.ModuleType("proxy")
    dummy_proxy.__path__ = []
    sys.modules["litellm_enterprise.proxy"] = dummy_proxy

    # Create dummy common_utils submodule with stub functions
    dummy_utils = types.ModuleType("common_utils")
    dummy_utils.__path__ = []
    dummy_utils.check_responses_cost = None
    dummy_utils.check_batch_cost = None
    sys.modules["litellm_enterprise.proxy.common_utils"] = dummy_utils

    print('[OK] Enterprise modules mocked', flush=True)


def main():
    """Start LiteLLM and monitor it continuously."""
    global shutdown_requested

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print('[INFO] Preparing LiteLLM environment...', flush=True)

    # CRITICAL: Mock enterprise modules BEFORE subprocess starts
    mock_enterprise_modules()

    # Load .env file
    print('[INFO] Loading .env file...', flush=True)
    env_vars = load_env()

    # Verify DATABASE_URL exists
    database_url = get_database_url(env_vars)
    print('[OK] DATABASE_URL loaded', flush=True)

    # Fix config.yaml to use actual DATABASE_URL instead of placeholder
    config_file = Path(__file__).parent / 'config.yaml'
    if config_file.exists():
        content = config_file.read_text()
        content = content.replace('database_url: env/DATABASE_URL', f'database_url: {database_url}')
        config_file.write_text(content)
        print('[OK] Updated config.yaml with DATABASE_URL', flush=True)

    # Get LiteLLM port from .env (defaults to 11435)
    litellm_port = env_vars.get('LITELLM_PORT', '11435')
    print(f'[INFO] Using LiteLLM port {litellm_port}', flush=True)

    # PostgreSQL verification
    pg_port = None
    if 'postgresql' in database_url.lower():
        print('[INFO] Using PostgreSQL database', flush=True)
        print('[INFO] Verifying PostgreSQL is accepting connections...', flush=True)
        pg = PostgreSQLManager()
        if not pg.wait_for_ready(timeout=30):
            print('[ERROR] PostgreSQL is not accepting connections', flush=True)
            sys.exit(1)
        print('[OK] PostgreSQL is ready', flush=True)

        # Get actual port PostgreSQL is using
        pg_port = pg.port
        print(f'[INFO] PostgreSQL is using port {pg_port}', flush=True)

        # Update DATABASE_URL with actual PostgreSQL port using proper URL parsing
        try:
            parsed = urlparse(database_url)
            if parsed.port != pg_port:
                # Reconstruct URL with correct port
                new_netloc = f'{parsed.username}:{parsed.password}@{parsed.hostname}:{pg_port}'
                database_url = urlunparse((
                    parsed.scheme,
                    new_netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
                print(f'[INFO] Updated DATABASE_URL to use port {pg_port}', flush=True)
        except Exception as e:
            print(f'[WARN] Failed to update DATABASE_URL: {e}', flush=True)

    # Generate Prisma client BEFORE starting LiteLLM
    print('[INFO] Preparing Prisma database client...', flush=True)
    if not generate_prisma_client():
        print('[ERROR] Failed to generate Prisma client', flush=True)
        sys.exit(1)

    print('[INFO] Starting LiteLLM...', flush=True)

    # Prepare subprocess environment
    process_env = os.environ.copy()
    process_env.update(env_vars)
    process_env['DATABASE_URL'] = database_url
    process_env['PYTHONIOENCODING'] = 'utf-8'
    process_env['PYTHONUTF8'] = '1'
    process_env['PYTHONLEGACYWINDOWSSTDIO'] = '1'

    # Windows process isolation flags
    creation_flags = 0
    if sys.platform == 'win32':
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

    try:
        # Start LiteLLM directly (no wrapper script needed since modules are mocked)
        process = subprocess.Popen(
            [
                sys.executable,
                '-m', 'litellm',
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

        print(f'[INFO] LiteLLM process started (PID: {process.pid})', flush=True)

        # Monitor output and check for startup
        startup_complete = False
        startup_timeout = time.time() + 60

        while not startup_complete and not shutdown_requested:
            # Check if process died
            poll_result = process.poll()
            if poll_result is not None:
                print(f'[ERROR] LiteLLM process exited with code {poll_result}', flush=True)
                remaining = process.stdout.read()
                if remaining:
                    print(remaining, flush=True)
                sys.exit(poll_result if poll_result != 0 else 1)

            # Check if startup timeout exceeded
            if time.time() > startup_timeout:
                print('[ERROR] LiteLLM startup timeout (60 seconds)', flush=True)
                process.terminate()
                sys.exit(1)

            # Read available output
            try:
                line = process.stdout.readline()
                if line:
                    print(line.rstrip(), flush=True)
                    if 'Application startup complete' in line or 'Uvicorn running' in line:
                        startup_complete = True
                        break
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f'[WARN] Error reading output: {e}', flush=True)
                time.sleep(0.1)

        if shutdown_requested:
            process.terminate()
            sys.exit(0)

        # Verify LiteLLM is actually listening
        print('[INFO] Waiting for LiteLLM to accept connections...', flush=True)
        if not is_litellm_ready(port=litellm_port, timeout=30):
            print(f'[ERROR] LiteLLM is not accepting connections on port {litellm_port}', flush=True)
            process.terminate()
            sys.exit(1)

        print('[OK] LiteLLM is ready', flush=True)
        print('[OK] Uvicorn running', flush=True)
        print('[INFO] Entering monitoring mode - will stay running', flush=True)

        # Save subprocess PID for reference
        with open('litellm_server.pid', 'w') as f:
            f.write(str(process.pid))

        # Monitor until exit or signal
        try:
            while not shutdown_requested:
                if process.poll() is not None:
                    exit_code = process.poll()
                    print(f'[ERROR] LiteLLM process exited with code {exit_code}', flush=True)
                    remaining = process.stdout.read()
                    if remaining:
                        print(f'[ERROR] LiteLLM output: {remaining[:500]}', flush=True)
                    sys.exit(exit_code)
                time.sleep(1)

        except KeyboardInterrupt:
            print('\n[INFO] Shutdown signal received', flush=True)

    except FileNotFoundError:
        print('[ERROR] LiteLLM command not found. Is it installed?', flush=True)
        print('[ERROR] Try: pip install litellm[proxy]', flush=True)
        sys.exit(1)
    except Exception as e:
        print(f'[ERROR] LiteLLM failed: {e}', flush=True)
        sys.exit(1)
    finally:
        # Clean shutdown
        if 'process' in dir() and process and process.poll() is None:
            print('[INFO] Terminating LiteLLM process...', flush=True)
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print('[WARN] LiteLLM did not respond to terminate, killing...', flush=True)
                process.kill()
                process.wait()

        # Clean up PID file
        try:
            if os.path.exists('litellm_server.pid'):
                os.remove('litellm_server.pid')
        except Exception:
            pass

        print('[INFO] LiteLLM exiting', flush=True)


if __name__ == '__main__':
    main()
