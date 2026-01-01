"""Validate environment before starting services."""
import sys

from postgres_config import DATA_DIR, BIN_DIR, PG_CTL
from env_loader import get_database_url, load_env


def validate_environment():
    """Run all validation checks.

    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []

    # Check PostgreSQL installation
    if not BIN_DIR.exists():
        errors.append('PostgreSQL not installed (missing bin directory)')
    elif not PG_CTL.exists():
        errors.append(f'pg_ctl not found at {PG_CTL}')

    # Check data directory
    if not DATA_DIR.exists():
        errors.append(f'PostgreSQL data directory not found at {DATA_DIR}')

    # Check .env file
    try:
        env_vars = load_env()
        get_database_url(env_vars)
    except SystemExit:
        errors.append('.env file missing or invalid')
    except Exception as e:
        errors.append(f'Environment validation failed: {e}')

    return errors


def main():
    """Validate and report."""
    errors = validate_environment()

    if errors:
        print('[ERROR] Configuration validation failed:', flush=True)
        for error in errors:
            print(f'  - {error}', flush=True)
        sys.exit(1)

    print('[OK] Environment validated', flush=True)


if __name__ == '__main__':
    main()
