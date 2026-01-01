"""Utility for loading .env files."""
import os
import sys
from urllib.parse import urlparse


def get_password_from_url(database_url):
    """Extract password from PostgreSQL URL safely.

    Handles URL-encoded passwords and special characters correctly.

    Args:
        database_url: PostgreSQL connection string

    Returns:
        str: The password, or None if not found
    """
    try:
        parsed = urlparse(database_url)
        return parsed.password  # Automatically handles URL decoding
    except Exception:
        return None


def load_env(env_file='.env'):
    """Load environment variables from .env file.

    Args:
        env_file: Path to the .env file (default: '.env')

    Returns:
        dict: Environment variables including those from the .env file
    """
    if not os.path.exists(env_file):
        print(f'[ERROR] {env_file} not found', flush=True)
        sys.exit(1)

    env_vars = os.environ.copy()

    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def get_database_url(env_vars=None):
    """Get and validate DATABASE_URL from environment.

    Validates the URL format to catch configuration errors early
    with clear error messages.

    Args:
        env_vars: Dictionary of environment variables (optional)

    Returns:
        str: The validated DATABASE_URL value
    """
    if env_vars is None:
        env_vars = os.environ

    database_url = env_vars.get('DATABASE_URL')
    if not database_url:
        print('[ERROR] DATABASE_URL not found in environment', flush=True)
        sys.exit(1)

    # Validate format
    try:
        parsed = urlparse(database_url)

        if parsed.scheme not in ('postgresql', 'postgres'):
            print(f'[ERROR] DATABASE_URL must use postgresql:// scheme, got: {parsed.scheme}', flush=True)
            sys.exit(1)

        if not parsed.hostname:
            print('[ERROR] DATABASE_URL missing hostname', flush=True)
            sys.exit(1)

        if not parsed.path or parsed.path == '/':
            print('[ERROR] DATABASE_URL missing database name', flush=True)
            sys.exit(1)

    except Exception as e:
        print(f'[ERROR] Invalid DATABASE_URL format: {e}', flush=True)
        sys.exit(1)

    return database_url
