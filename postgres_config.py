"""PostgreSQL configuration and paths."""
import os
import socket
import sys
import time
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


def is_port_in_use(port, retries=3):
    """Check if a port is in use."""
    for attempt in range(retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                result = s.connect_ex(('127.0.0.1', port))
                
                if result == 0:
                    return True  # Connected = port IN USE
                return False    # Failed = port FREE (return immediately)
                
        except Exception:
            pass
        
        if attempt < retries - 1:
            time.sleep(0.1)
    
    return False  # Port is FREE


def _is_port_free(port):
    """Check if port is free (convenience wrapper).

    Returns:
        bool: True if port is free, False if in use
    """
    return not is_port_in_use(port, retries=1)


def _get_pg_port():
    """Get PostgreSQL port from DATABASE_URL in .env or environment variable."""
    # Check environment variable first
    env_port = os.environ.get('PG_PORT')
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass
    
    # Try to extract from DATABASE_URL in .env
    try:
        from env_loader import load_env
        env_vars = load_env()
        database_url = env_vars.get('DATABASE_URL', '')
        if database_url and ':5' in database_url:
            # Extract port from URL like postgresql://user:pass@localhost:5450/db
            parts = database_url.split(':')
            for i, part in enumerate(parts):
                if part.isdigit() and len(part) == 4 and part.startswith('5'):
                    return int(part)
    except:
        pass
    
    # Default to 5450
    return 5450


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


