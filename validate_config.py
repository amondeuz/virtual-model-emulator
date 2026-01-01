"""Validate environment before starting services."""
import sys

from postgres_config import DATA_DIR, BIN_DIR, PG_CTL
from env_loader import get_database_url, load_env


def validate_environment():
    """Run all validation checks.

    Returns:
        list: List of (error_message, fix_suggestion) tuples
    """
    errors = []

    # Check PostgreSQL installation
    if not BIN_DIR.exists():
        errors.append((
            'PostgreSQL not installed (missing bin directory)',
            'Run install again to download PostgreSQL'
        ))
    elif not PG_CTL.exists():
        errors.append((
            f'pg_ctl not found at {PG_CTL}',
            'Run install again to download PostgreSQL'
        ))

    # Check data directory
    if not DATA_DIR.exists():
        errors.append((
            f'PostgreSQL data directory not found at {DATA_DIR}',
            'Run install again to initialize the database'
        ))

    # Check .env file and DATABASE_URL format
    try:
        env_vars = load_env()
        get_database_url(env_vars)  # This validates the URL format
    except SystemExit:
        errors.append((
            '.env file missing or invalid',
            'Run install again to regenerate .env file'
        ))
    except Exception as e:
        errors.append((
            f'Environment validation failed: {e}',
            'Check .env file format or run install again'
        ))

    return errors


def main():
    """Validate and report."""
    errors = validate_environment()

    if errors:
        print('[ERROR] Configuration validation failed:', flush=True)
        for error_msg, fix_suggestion in errors:
            print(f'  - {error_msg}', flush=True)
            print(f'    FIX: {fix_suggestion}', flush=True)
        sys.exit(1)

    print('[OK] Environment validated', flush=True)


if __name__ == '__main__':
    main()
