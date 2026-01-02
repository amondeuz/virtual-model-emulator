"""PostgreSQL lifecycle management."""
import os
import subprocess
import time

from postgres_config import (
    PG_CTL, CREATEDB, PG_ISREADY, DATA_DIR, LOG_FILE,
    PG_PORT, PG_USER, PG_HOST, PG_DATABASE, print_error,
    is_port_in_use
)
from env_loader import load_env, get_password_from_url


def find_open_port(start_port=5450, max_attempts=100):
    """Find an open port starting from start_port.

    CRITICAL FIX: Increased max_attempts from 10 to 100
    This allows searching ports 5450-5550 instead of just 5432-5441.
    When v2.0.0 and v2.1.2 run together, this prevents "all ports in use" errors.

    Args:
        start_port: Port to start checking from
        max_attempts: Maximum ports to check (100 = 5450-5550)

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
        """Wait for PostgreSQL to accept connections."""
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            # Just check if port is accepting connections
            # Don't use pg_isready - it has auth issues
            if not is_port_in_use(self.port):
                # Port opened but not listening yet, wait a bit
                time.sleep(0.5)
                continue
            
            # Port is listening - that means PostgreSQL is accepting connections
            return True
        
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
            
        # Disable WAL replication in postgresql.conf to prevent crashes on Windows
        config_file = self.data_dir / 'postgresql.conf'
        if config_file.exists():
            content = config_file.read_text()
            modified = False
        
            # Fix wal_level
            if 'wal_level = replica' in content:
                content = content.replace('wal_level = replica', 'wal_level = minimal')
                modified = True
            elif 'wal_level = minimal' not in content:
                content += '\nwal_level = minimal\n'
                modified = True
            
            # Fix max_wal_senders
            if 'max_wal_senders = ' in content and 'max_wal_senders = 0' not in content:
                # Comment out any existing max_wal_senders line
                lines = content.split('\n')
                content = '\n'.join([f'#{line}' if line.startswith('max_wal_senders = ') else line for line in lines])
                modified = True
            
            if 'max_wal_senders = 0' not in content:
                content += 'max_wal_senders = 0\n'
                modified = True
        
            if modified:
                config_file.write_text(content)
                print('[OK] Disabled WAL replication in postgresql.conf', flush=True)
                
        # Check if port is available, try to find open port if needed
        if is_port_in_use(self.port):
            print(f'[WARN] Port {self.port} already in use', flush=True)
            open_port = find_open_port(self.port, max_attempts=100)
            if open_port:
                print(f'[INFO] Using port {open_port} instead', flush=True)
                self.port = open_port
            else:
                print('[ERROR] All PostgreSQL ports (5450-5550) are in use!', flush=True)
                print('[ERROR] Close other PostgreSQL instances or database applications.', flush=True)
                print('[ERROR] Or set PG_PORT environment variable to a specific free port.', flush=True)
                return False

        # Start server
        try:
            print('[INFO] Starting PostgreSQL server...', flush=True)
            subprocess.Popen([
                str(PG_CTL.resolve()), 'start',
                '-D', str(self.data_dir.resolve()),
                '-l', str(self.log_file.resolve()),
                '-o', f'-p {self.port} -c max_wal_senders=0 -c wal_level=minimal'
            ])
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
                '-h', self.host,
                '-p', str(self.port),
                '-U', self.user,
                dbname
            ], capture_output=True, text=True, timeout=10, env=self.pg_env)

            if result.returncode == 0:
                print(f'[OK] Database {dbname} created', flush=True)
                return True
            elif 'already exists' in result.stderr:
                print(f'[OK] Database {dbname} exists', flush=True)
                return True
            elif 'password authentication failed' in result.stderr.lower() or \
                 'permission denied' in result.stderr.lower():
                print('[ERROR] Database password mismatch!', flush=True)
                print('[ERROR] PostgreSQL was initialized with a different password.', flush=True)
                print('[ERROR] To fix: Delete postgres/ directory and .env file, then run install again.', flush=True)
                return False
            else:
                print(f'[WARN] createdb: {result.stderr}', flush=True)
                return False

        except Exception as e:
            print(f'[WARN] Database creation failed: {e}', flush=True)
            return False











