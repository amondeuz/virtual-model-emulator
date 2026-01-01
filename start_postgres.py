"""Start PostgreSQL server before running the app."""
import os
import socket
import subprocess
import time
import sys

from postgres_config import (
    PG_CTL, PSQL, CREATEDB, PG_ISREADY, DATA_DIR, LOG_FILE,
    PG_PORT, PG_USER, PG_HOST, PG_DATABASE, print_error
)
from env_loader import load_env, get_password_from_url


def is_port_in_use(port, retries=3):
    """Check if a port is already in use (Windows-compatible with retries).

    Args:
        port: Port number to check
        retries: Number of retry attempts for uncertain results

    Returns:
        bool: True if port is in use, False otherwise
    """
    for attempt in range(retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                result = s.connect_ex(('localhost', port))

                if result == 0:
                    # Port is definitely in use
                    return True
                elif result == 10061:  # Windows WSAECONNREFUSED
                    # Port is definitely NOT in use
                    return False
                elif result == 111:  # Linux ECONNREFUSED
                    # Port is definitely NOT in use
                    return False
                # Other errors - retry

        except socket.error:
            pass

        if attempt < retries - 1:
            time.sleep(0.2)

    # If uncertain after retries, assume port is free
    return False


def wait_for_postgres(timeout=30):
    """Wait for PostgreSQL to accept connections using pg_isready.

    Uses the official pg_isready tool which is more reliable and faster
    than attempting psql connections, especially on Windows.

    Args:
        timeout: Maximum seconds to wait

    Returns:
        bool: True if PostgreSQL is accepting connections
    """
    start_time = time.time()
    # Resolve path once for Windows compatibility (handles spaces in paths)
    pg_isready_path = str(PG_ISREADY.resolve())

    while time.time() - start_time < timeout:
        try:
            result = subprocess.run([
                pg_isready_path,
                '-h', PG_HOST,
                '-p', str(PG_PORT),
                '-U', PG_USER,
                '-t', '3'  # pg_isready's internal timeout (seconds)
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        time.sleep(0.5)

    return False


def get_pg_env():
    """Get environment variables for PostgreSQL commands."""
    env = os.environ.copy()
    # Load password from .env if available
    try:
        env_vars = load_env()
        database_url = env_vars.get('DATABASE_URL', '')
        # Extract password using urllib.parse for safe handling
        # of special characters and URL-encoded passwords
        password = get_password_from_url(database_url)
        if password:
            env['PGPASSWORD'] = password
    except SystemExit:
        pass  # .env doesn't exist yet during initial install
    return env


def check_postgres_running():
    """Check if PostgreSQL is already running."""
    try:
        # Resolve paths for Windows compatibility (handles spaces in paths)
        result = subprocess.run(
            [str(PG_CTL.resolve()), 'status', '-D', str(DATA_DIR.resolve())],
            capture_output=True,
            text=True,
            timeout=5
        )
        return 'server is running' in result.stdout
    except Exception:
        return False


def start_postgres():
    """Start PostgreSQL server."""
    print('[INFO] Starting PostgreSQL...', flush=True)

    # Validate DATA_DIR exists before attempting to start
    if not DATA_DIR.exists():
        print_error('data_dir_corrupt',
                   'PostgreSQL data directory not found. Run install again.')
        return False

    # Check if already running
    if check_postgres_running():
        print('[OK] PostgreSQL already running', flush=True)
        return True

    # Check if port is available
    if is_port_in_use(PG_PORT):
        print_error('port_in_use')
        return False

    # Start PostgreSQL with -w flag to wait for startup
    try:
        print('[INFO] Starting PostgreSQL server...', flush=True)
        # Resolve all paths for Windows compatibility (handles spaces in paths)
        result = subprocess.run([
            str(PG_CTL.resolve()), 'start',
            '-w',  # Wait for startup to complete
            '-t', '30',  # Timeout after 30 seconds
            '-D', str(DATA_DIR.resolve()),
            '-l', str(LOG_FILE.resolve()),
            '-o', f'-p {PG_PORT}'
        ], capture_output=True, text=True, timeout=35)

        if result.returncode != 0:
            print(f'[ERROR] pg_ctl failed: {result.stderr}', flush=True)
            return False

        print('[OK] PostgreSQL started', flush=True)

    except subprocess.TimeoutExpired:
        print_error('timeout')
        return False
    except Exception as e:
        print(f'[ERROR] Failed to start: {e}', flush=True)
        return False

    # Wait for PostgreSQL to accept connections (proper race condition fix)
    print('[INFO] Waiting for PostgreSQL to accept connections...', flush=True)
    if not wait_for_postgres(timeout=30):
        print_error('connection_failed', 'PostgreSQL started but not accepting connections')
        return False

    print('[OK] PostgreSQL accepting connections', flush=True)
    return True


def create_database():
    """Create litellm database if it doesn't exist."""
    try:
        print('[INFO] Creating litellm database...', flush=True)
        # Resolve path for Windows compatibility (handles spaces in paths)
        result = subprocess.run(
            [str(CREATEDB.resolve()), '-U', PG_USER, PG_DATABASE],
            capture_output=True,
            text=True,
            timeout=10,
            env=get_pg_env()
        )
        # Ignore error if database already exists
        if result.returncode != 0:
            if 'already exists' in result.stderr:
                print('[OK] Database already exists', flush=True)
            else:
                print(f'[WARN] createdb: {result.stderr}', flush=True)
        else:
            print('[OK] Database created', flush=True)
        return True
    except Exception as e:
        print(f'[WARN] createdb failed: {e}', flush=True)
        return False


def main():
    """Main entry point."""
    if not start_postgres():
        sys.exit(1)

    create_database()

    print('[OK] PostgreSQL ready', flush=True)


if __name__ == '__main__':
    main()
