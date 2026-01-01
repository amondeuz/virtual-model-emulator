"""PostgreSQL configuration and paths."""
import os
import socket
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
POSTGRES_DIR = BASE_DIR / 'postgres'
BIN_DIR = POSTGRES_DIR / 'bin'
DATA_DIR = POSTGRES_DIR / 'data'
LOG_FILE = POSTGRES_DIR / 'logfile'

# Executables (cross-platform)
EXE_EXT = '.exe' if sys.platform == 'win32' else ''
PG_CTL = BIN_DIR / f'pg_ctl{EXE_EXT}'
INITDB = BIN_DIR / f'initdb{EXE_EXT}'
CREATEDB = BIN_DIR / f'createdb{EXE_EXT}'
PSQL = BIN_DIR / f'psql{EXE_EXT}'
PG_ISREADY = BIN_DIR / f'pg_isready{EXE_EXT}'


def _is_port_free(port):
    """Quick check if port is free without retries."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(('localhost', port))
            # Connection refused means port is free
            if sys.platform == 'win32' and result == 10061:
                return True
            if sys.platform != 'win32' and result in (111, 61):
                return True
            return result != 0  # Non-zero and not refused = likely free
    except socket.error:
        return True  # Error = assume free


def _get_pg_port():
    """Get PostgreSQL port from environment or find an available one.

    Priority:
    1. PG_PORT environment variable
    2. Default port 5432 if available
    3. Fallback to 5433, 5434, etc. if default is in use
    """
    # Check environment variable first
    env_port = os.environ.get('PG_PORT')
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass

    # Try default port
    default_port = 5432
    if _is_port_free(default_port):
        return default_port

    # Fallback: try alternative ports
    for offset in range(1, 10):
        alt_port = default_port + offset
        if _is_port_free(alt_port):
            print(f'[INFO] Port {default_port} in use, using {alt_port} instead', flush=True)
            return alt_port

    # Give up and use default (will fail later with clear error)
    return default_port


# Connection settings
PG_PORT = _get_pg_port()
PG_USER = 'postgres'
PG_DATABASE = 'litellm'
PG_HOST = 'localhost'

# Error messages with actionable guidance
ERROR_MESSAGES = {
    'port_in_use': f'[ERROR] Port {PG_PORT} is already in use. Stop other PostgreSQL instances or set PG_PORT environment variable.',
    'data_dir_corrupt': '[ERROR] PostgreSQL data directory is corrupted. Delete postgres/data and reinstall.',
    'timeout': '[ERROR] PostgreSQL startup timed out. Check postgres/logfile for details.',
    'permission': '[ERROR] Permission denied. Run Pinokio as administrator.',
    'connection_failed': '[ERROR] Cannot connect to PostgreSQL. Check if the server is running.',
    'createdb_failed': '[ERROR] Failed to create database. Check postgres/logfile for details.',
}


def get_connection_params():
    """Get PostgreSQL connection parameters."""
    return {
        'host': PG_HOST,
        'port': PG_PORT,
        'user': PG_USER,
        'database': PG_DATABASE
    }


def print_error(error_type, details=None):
    """Print an actionable error message."""
    message = ERROR_MESSAGES.get(error_type, f'[ERROR] {error_type}')
    if details:
        message += f'\nDetails: {details}'
    print(message, flush=True)
