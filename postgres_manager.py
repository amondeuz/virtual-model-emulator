"""PostgreSQL lifecycle management."""
import os
import socket
import subprocess
import sys
import time

from postgres_config import (
    PG_CTL, CREATEDB, PG_ISREADY, DATA_DIR, LOG_FILE,
    PG_PORT, PG_USER, PG_HOST, PG_DATABASE, print_error
)
from env_loader import load_env, get_password_from_url


def is_port_in_use(port, retries=3):
    """Check if a port is in use (Windows-compatible with retries).

    Args:
        port: Port number to check
        retries: Number of retry attempts for uncertain results

    Returns:
        bool: True if port is in use or uncertain, False only if definitely free
    """
    for attempt in range(retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                result = s.connect_ex(('localhost', port))

                # Definitive answers - return immediately
                if result == 0:
                    return True  # Port is in use

                # Connection refused - port is free (platform-specific codes)
                # Windows: WSAECONNREFUSED = 10061
                # Linux: ECONNREFUSED = 111
                # macOS: ECONNREFUSED = 61
                if sys.platform == 'win32' and result == 10061:
                    return False
                if sys.platform != 'win32' and result in (111, 61):
                    return False

                # Uncertain result - will retry

        except socket.error:
            # Socket error - will retry
            pass

        if attempt < retries - 1:
            time.sleep(0.2)

    # After all retries with uncertain result, assume port IS in use (fail closed for safety)
    # This prevents initdb/pg_ctl from failing cryptically if port is actually in use
    return True


def find_open_port(start_port=5432, max_attempts=10):
    """Find an open port starting from start_port.

    Args:
        start_port: Port to start checking from
        max_attempts: Maximum ports to check

    Returns:
        int: First open port found, or None if none available
    """
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    return None


class PostgreSQLManager:
    """Manages PostgreSQL server lifecycle."""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.log_file = LOG_FILE
        self.port = PG_PORT
        self.user = PG_USER
        self.host = PG_HOST
        self.database = PG_DATABASE
        self._env = None

    @property
    def pg_env(self):
        """Get PostgreSQL environment variables (cached)."""
        if self._env is None:
            self._env = os.environ.copy()
            try:
                env_vars = load_env()
                password = get_password_from_url(env_vars.get('DATABASE_URL', ''))
                if password:
                    self._env['PGPASSWORD'] = password
            except SystemExit:
                pass  # .env doesn't exist yet during initial install
        return self._env

    def is_running(self):
        """Check if PostgreSQL is running.

        Returns:
            bool: True if server is running
        """
        try:
            result = subprocess.run([
                str(PG_CTL.resolve()), 'status',
                '-D', str(self.data_dir.resolve())
            ], capture_output=True, text=True, timeout=5)
            # Use return code for reliability (0 = running, non-zero = not running)
            # This is more reliable than text matching across platforms/locales
            return result.returncode == 0
        except Exception:
            return False

    def wait_for_ready(self, timeout=30):
        """Wait for PostgreSQL to accept connections.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            bool: True if PostgreSQL is accepting connections
        """
        start = time.time()
        pg_isready_path = str(PG_ISREADY.resolve())

        while time.time() - start < timeout:
            try:
                result = subprocess.run([
                    pg_isready_path,
                    '-h', self.host,
                    '-p', str(self.port),
                    '-U', self.user,
                    '-t', '3'  # pg_isready's internal timeout (seconds)
                ], capture_output=True, text=True, timeout=5)

                if result.returncode == 0:
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        return False

    def start(self, timeout=30):
        """Start PostgreSQL server.

        Args:
            timeout: Maximum seconds to wait for startup

        Returns:
            bool: True if started successfully
        """
        print('[INFO] Starting PostgreSQL...', flush=True)

        # Validate data directory exists
        if not self.data_dir.exists():
            print_error('data_dir_corrupt',
                       'PostgreSQL data directory not found. Run install again.')
            return False

        # Check if already running
        if self.is_running():
            print('[OK] PostgreSQL already running', flush=True)
            return True

        # Check if port is available, try to find open port if needed
        if is_port_in_use(self.port):
            print(f'[WARN] Port {self.port} already in use', flush=True)
            open_port = find_open_port(self.port, max_attempts=10)
            if open_port:
                print(f'[INFO] Using port {open_port} instead', flush=True)
                self.port = open_port
            else:
                print_error('port_in_use')
                return False

        # Start server
        try:
            print('[INFO] Starting PostgreSQL server...', flush=True)
            result = subprocess.run([
                str(PG_CTL.resolve()), 'start',
                '-w', '-t', str(timeout),
                '-D', str(self.data_dir.resolve()),
                '-l', str(self.log_file.resolve()),
                '-o', f'-p {self.port}'
            ], capture_output=True, text=True, timeout=timeout + 5)

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

        # Wait for connections
        print('[INFO] Waiting for PostgreSQL to accept connections...', flush=True)
        if not self.wait_for_ready(timeout=timeout):
            print_error('connection_failed',
                       'PostgreSQL started but not accepting connections')
            return False

        print('[OK] PostgreSQL accepting connections', flush=True)
        return True

    def stop(self, mode='fast', timeout=30):
        """Stop PostgreSQL server.

        Args:
            mode: 'fast', 'smart', or 'immediate'
            timeout: Maximum seconds to wait

        Returns:
            bool: True if stopped successfully
        """
        print('[INFO] Stopping PostgreSQL...', flush=True)

        try:
            result = subprocess.run([
                str(PG_CTL.resolve()), 'stop',
                '-D', str(self.data_dir.resolve()),
                '-m', mode
            ], capture_output=True, text=True, timeout=timeout)

            if result.returncode == 0:
                print('[OK] PostgreSQL stopped', flush=True)
                return True
            elif 'not running' in result.stderr.lower():
                print('[OK] PostgreSQL was not running', flush=True)
                return True
            else:
                print(f'[WARN] Stop issue: {result.stderr}', flush=True)
                return False

        except subprocess.TimeoutExpired:
            # Try immediate shutdown
            print('[WARN] Graceful stop timed out, forcing immediate shutdown...',
                  flush=True)
            try:
                subprocess.run([
                    str(PG_CTL.resolve()), 'stop',
                    '-D', str(self.data_dir.resolve()),
                    '-m', 'immediate'
                ], capture_output=True, timeout=10)
                print('[OK] PostgreSQL stopped (immediate)', flush=True)
                return True
            except Exception:
                print('[ERROR] Failed to stop PostgreSQL', flush=True)
                return False

        except Exception as e:
            print(f'[ERROR] Stop failed: {e}', flush=True)
            return False

    def create_database(self, dbname=None):
        """Create database if it doesn't exist.

        Args:
            dbname: Database name (defaults to configured database)

        Returns:
            bool: True if database exists or was created
        """
        if dbname is None:
            dbname = self.database

        try:
            print(f'[INFO] Creating {dbname} database...', flush=True)
            result = subprocess.run([
                str(CREATEDB.resolve()),
                '-U', self.user,
                dbname
            ], capture_output=True, text=True, timeout=10, env=self.pg_env)

            if result.returncode == 0:
                print(f'[OK] Database {dbname} created', flush=True)
                return True
            elif 'already exists' in result.stderr:
                print(f'[OK] Database {dbname} exists', flush=True)
                return True
            else:
                print(f'[WARN] createdb: {result.stderr}', flush=True)
                return False

        except Exception as e:
            print(f'[WARN] Database creation failed: {e}', flush=True)
            return False
