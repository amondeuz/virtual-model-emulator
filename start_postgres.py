"""Start PostgreSQL server before running the app."""
import os
import socket
import subprocess
import time
import sys

from postgres_config import (
    PG_CTL, PSQL, CREATEDB, DATA_DIR, LOG_FILE,
    PG_PORT, PG_USER, PG_DATABASE, print_error
)
from env_loader import load_env


def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def wait_for_postgres(timeout=30):
    """Wait for PostgreSQL to accept connections.

    Args:
        timeout: Maximum seconds to wait

    Returns:
        bool: True if PostgreSQL is accepting connections
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                [str(PSQL), '-U', PG_USER, '-d', 'postgres', '-c', 'SELECT 1'],
                capture_output=True,
                text=True,
                timeout=5,
                env=get_pg_env()
            )
            if result.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        time.sleep(1)

    return False


def get_pg_env():
    """Get environment variables for PostgreSQL commands."""
    env = os.environ.copy()
    # Load password from .env if available
    try:
        env_vars = load_env()
        database_url = env_vars.get('DATABASE_URL', '')
        # Extract password from DATABASE_URL
        # Format: postgresql://user:password@host:port/database
        if ':' in database_url and '@' in database_url:
            # Get the part between :// and @
            auth_part = database_url.split('://')[1].split('@')[0]
            if ':' in auth_part:
                password = auth_part.split(':')[1]
                env['PGPASSWORD'] = password
    except SystemExit:
        pass  # .env doesn't exist yet during initial install
    return env


def check_postgres_running():
    """Check if PostgreSQL is already running."""
    try:
        result = subprocess.run(
            [str(PG_CTL), 'status', '-D', str(DATA_DIR)],
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
        result = subprocess.run([
            str(PG_CTL), 'start',
            '-w',  # Wait for startup to complete
            '-t', '30',  # Timeout after 30 seconds
            '-D', str(DATA_DIR),
            '-l', str(LOG_FILE),
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
        result = subprocess.run(
            [str(CREATEDB), '-U', PG_USER, PG_DATABASE],
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
