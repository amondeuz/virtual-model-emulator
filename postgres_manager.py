"""PostgreSQL Manager - Handles startup, shutdown, and readiness checks."""
import os
import subprocess
import sys
import time
import socket
from pathlib import Path

# Import paths
BASE_DIR = Path(__file__).parent
POSTGRES_DIR = BASE_DIR / 'postgres'
BIN_DIR = POSTGRES_DIR / 'bin'

# Configuration
PG_HOST = os.environ.get('PG_HOST', '127.0.0.1')
PG_USER = os.environ.get('PG_USER', 'postgres')
PG_DATABASE = os.environ.get('PG_DATABASE', 'litellm')
PG_PORT_DEFAULT = int(os.environ.get('PG_PORT', 5450))
DATA_DIR = POSTGRES_DIR / 'data'
LOG_FILE = POSTGRES_DIR / 'logfile'

# Platform-specific paths
if sys.platform == 'win32':
    PG_CTL = BIN_DIR / 'pg_ctl.exe'
    INITDB = BIN_DIR / 'initdb.exe'
    PG_ISREADY = BIN_DIR / 'pg_isready.exe'
else:
    PG_CTL = BIN_DIR / 'pg_ctl'
    INITDB = BIN_DIR / 'initdb'
    PG_ISREADY = BIN_DIR / 'pg_isready'


class PostgreSQLManager:
    """Manage PostgreSQL server lifecycle."""

    def __init__(self):
        """Initialize PostgreSQL manager."""
        self.data_dir = DATA_DIR
        self.log_file = LOG_FILE
        self._port = None  # Dynamic port (initialized at runtime)
        self.user = PG_USER
        self.host = PG_HOST
        self.database = PG_DATABASE
        self._env = None
        self.process = None
        print('[DEBUG] PostgreSQL manager initialized', flush=True)

    @property
    def port(self):
        """Get current port (may change at runtime)."""
        if self._port is None:
            self._port = PG_PORT_DEFAULT
        return self._port

    @port.setter
    def port(self, value):
        """Set port dynamically."""
        print(f'[DEBUG] Port changing from {self._port} to {value}', flush=True)
        self._port = value

    @property
    def pg_env(self):
        """Get environment with PGPASSWORD set."""
        if self._env is None:
            try:
                from env_loader import load_env, get_password_from_url
                env_vars = load_env()
                database_url = env_vars.get('DATABASE_URL', '')
                password = get_password_from_url(database_url)

                if not password:
                    print('[WARN] No password found in DATABASE_URL', flush=True)
                    password = 'postgres'  # Fallback

                self._env = os.environ.copy()
                self._env['PGPASSWORD'] = password

            except SystemExit:
                # env_loader tried to exit, catch and use defaults
                print('[WARN] env_loader failed, using default password', flush=True)
                self._env = os.environ.copy()
                self._env['PGPASSWORD'] = 'postgres'

        return self._env

    def find_open_port(self, start_port=5450, max_attempts=100):
        """Find an open port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                result = sock.connect_ex((self.host, port))
                sock.close()
                if result != 0:  # Port is available
                    return port
            except Exception:
                continue
        return None

    def is_running(self):
        """Check if PostgreSQL process is running."""
        try:
            result = subprocess.run([
                str(PG_CTL.resolve()), 'status',
                '-D', str(self.data_dir.resolve())
            ], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def wait_for_ready(self, timeout=30):
        """Wait for PostgreSQL to accept connections."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Method 1: Try pg_isready (most accurate)
            if PG_ISREADY.exists():
                try:
                    result = subprocess.run([
                        str(PG_ISREADY.resolve()),
                        '-h', self.host,
                        '-p', str(self.port),
                        '-U', self.user,
                        '-d', self.database
                    ], capture_output=True, text=True, timeout=2, env=self.pg_env)

                    if result.returncode == 0:
                        print(f'[OK] PostgreSQL ready on {self.host}:{self.port}', flush=True)
                        time.sleep(0.5)
                        return True
                except Exception:
                    pass

            # Method 2: Fallback to socket connection check
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.host, self.port))
                sock.close()

                if result == 0:
                    print(f'[OK] PostgreSQL listening on {self.host}:{self.port}', flush=True)
                    time.sleep(0.5)
                    return True
            except Exception:
                pass

            time.sleep(0.5)

        print(f'[ERROR] PostgreSQL not ready on {self.host}:{self.port} after {timeout}s', flush=True)
        return False

    def is_ready(self):
        """Quick check if PostgreSQL is ready."""
        return self.wait_for_ready(timeout=1)

    def start(self, timeout=30):
        """Start PostgreSQL server."""
        if self.is_running():
            print('[WARN] PostgreSQL already running', flush=True)
            return True

        print('[INFO] Starting PostgreSQL server...', flush=True)

        # Validate data directory exists
        if not self.data_dir.exists():
            print(f'[ERROR] Data directory not found: {self.data_dir}', flush=True)
            return False

        # Find open port if default is busy
        self.port = self.find_open_port(self.port)
        if not self.port:
            print('[ERROR] No available ports found', flush=True)
            return False

        if self.port != PG_PORT_DEFAULT:
            print(f'[INFO] Port {PG_PORT_DEFAULT} in use, using {self.port}', flush=True)

        # Windows-specific flags
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

        try:
            self.process = subprocess.Popen([
                str(PG_CTL.resolve()), 'start',
                '-D', str(self.data_dir.resolve()),
                '-l', str(self.log_file.resolve()),
                '-o', f'-p {self.port}'
            ], stdin=subprocess.DEVNULL, creationflags=creation_flags)

            # Wait for pg_ctl to complete
            try:
                self.process.wait(timeout=10)
                if self.process.returncode != 0:
                    print(f'[ERROR] pg_ctl failed with code {self.process.returncode}', flush=True)
                    return False
            except subprocess.TimeoutExpired:
                pass  # pg_ctl may still be running

            print('[OK] PostgreSQL started', flush=True)

            # Wait for connections to be accepted
            if not self.wait_for_ready(timeout):
                print('[ERROR] PostgreSQL failed to become ready', flush=True)
                return False

            return True

        except Exception as e:
            print(f'[ERROR] Failed to start PostgreSQL: {e}', flush=True)
            return False

    def create_database(self, timeout=10):
        """Create database if it doesn't exist."""
        try:
            # Try to connect - if successful, database exists
            import subprocess
            result = subprocess.run([
                str(PG_ISREADY.resolve()),
                '-h', self.host,
                '-p', str(self.port),
                '-U', self.user,
                '-d', self.database
            ], capture_output=True, text=True, timeout=2, env=self.pg_env)

            if result.returncode == 0:
                print(f'[OK] Database {self.database} exists', flush=True)
                return True
        except Exception:
            pass

        # Create database
        print(f'[INFO] Creating database {self.database}...', flush=True)
        try:
            result = subprocess.run([
                str((BIN_DIR / ('createdb.exe' if sys.platform == 'win32' else 'createdb')).resolve()),
                '-h', self.host,
                '-p', str(self.port),
                '-U', self.user,
                self.database
            ], capture_output=True, text=True, timeout=timeout, env=self.pg_env)

            if result.returncode == 0 or 'already exists' in result.stderr:
                print(f'[OK] Database {self.database} ready', flush=True)
                return True
            else:
                print(f'[ERROR] Database creation failed: {result.stderr}', flush=True)
                return False

        except subprocess.TimeoutExpired:
            print('[ERROR] Database creation timed out', flush=True)
            return False
        except Exception as e:
            print(f'[ERROR] Database creation error: {e}', flush=True)
            return False

    def stop(self, mode='fast', timeout=30):
        """Stop PostgreSQL server."""
        print('[INFO] Stopping PostgreSQL...', flush=True)

        # Method 1: Use stored process object if available
        if hasattr(self, 'process') and self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
                print('[OK] PostgreSQL stopped', flush=True)
                self.process = None
                return True
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                print('[OK] PostgreSQL stopped (forced)', flush=True)
                self.process = None
                return True
            except Exception as e:
                print(f'[WARN] Process termination failed: {e}', flush=True)

        # Method 2: Fallback to pg_ctl
        try:
            result = subprocess.run([
                str(PG_CTL.resolve()), 'stop',
                '-D', str(self.data_dir.resolve()),
                '-m', mode
            ], capture_output=True, text=True, timeout=timeout)

            if result.returncode == 0:
                print('[OK] PostgreSQL stopped', flush=True)
                return True
            else:
                print(f'[WARN] pg_ctl stop failed: {result.stderr}', flush=True)
                return False

        except subprocess.TimeoutExpired:
            print(f'[ERROR] PostgreSQL stop timed out after {timeout}s', flush=True)
            return False
        except Exception as e:
            print(f'[ERROR] Failed to stop PostgreSQL: {e}', flush=True)
            return False
