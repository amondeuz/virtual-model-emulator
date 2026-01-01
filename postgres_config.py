"""PostgreSQL configuration and paths."""
import os
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

# Connection settings
PG_PORT = 5432
PG_USER = 'postgres'
PG_DATABASE = 'litellm'
PG_HOST = 'localhost'

# Error messages with actionable guidance
ERROR_MESSAGES = {
    'port_in_use': '[ERROR] Port 5432 is already in use. Stop other PostgreSQL instances and try again.',
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
