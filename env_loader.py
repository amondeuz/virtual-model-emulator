"""Environment variable loader with safe defaults."""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def load_env(env_file='.env'):
    """Load environment variables from .env file with graceful fallback."""
    env_vars = os.environ.copy()

    if not os.path.exists(env_file):
        print(f'[INFO] {env_file} not found, using defaults', flush=True)
        # Provide defaults for first-time setup
        env_vars.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5450/litellm')
        env_vars.setdefault('LITELLM_PORT', '11435')
        env_vars.setdefault('API_SERVER_PORT', '8775')
        return env_vars

    try:
        with open(env_file, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove surrounding quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    env_vars[key] = value
        return env_vars
    except Exception as e:
        print(f'[WARN] Error loading {env_file}: {e}', flush=True)
        return env_vars


def get_password_from_url(database_url):
    """Extract password from PostgreSQL URL safely."""
    try:
        parsed = urlparse(database_url)
        return parsed.password
    except Exception:
        return None


def get_database_url(env_vars=None):
    """Get DATABASE_URL with graceful defaults and non-fatal validation."""
    if env_vars is None:
        env_vars = os.environ

    database_url = env_vars.get('DATABASE_URL')
    if not database_url:
        print('[INFO] DATABASE_URL not set, using default', flush=True)
        return 'postgresql://postgres:postgres@localhost:5450/litellm'

    try:
        parsed = urlparse(database_url)

        # Log warnings instead of exiting
        issues = []

        if parsed.scheme not in ('postgresql', 'postgres'):
            issues.append(f"scheme should be 'postgresql', got '{parsed.scheme}'")

        if not parsed.hostname:
            issues.append("missing hostname")

        if not parsed.username:
            issues.append("missing username")

        if not parsed.path or parsed.path == '/':
            issues.append("missing database name")

        if issues:
            print(f'[WARN] DATABASE_URL issues: {"; ".join(issues)}', flush=True)

        return database_url

    except Exception as e:
        print(f'[WARN] DATABASE_URL parse error: {e}', flush=True)
        return 'postgresql://postgres:postgres@localhost:5450/litellm'


def update_database_url_port(database_url, new_port):
    """Update port in DATABASE_URL safely."""
    try:
        parsed = urlparse(database_url)

        # Build new netloc with updated port
        netloc = parsed.hostname or 'localhost'
        if parsed.username:
            netloc = parsed.username + (':' + parsed.password if parsed.password else '') + '@' + netloc
        netloc = netloc + ':' + str(new_port)

        # Rebuild URL
        new_url = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        print(f'[INFO] Updated DATABASE_URL port to {new_port}', flush=True)
        return new_url
    except Exception as e:
        print(f'[WARN] Failed to update DATABASE_URL port: {e}', flush=True)
        return database_url
