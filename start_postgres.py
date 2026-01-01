"""Start PostgreSQL server before running the app."""
import subprocess
import sys

from postgres_manager import PostgreSQLManager


def main():
    """Main entry point."""
    pg = PostgreSQLManager()

    if not pg.start():
        sys.exit(1)

    # Create database with timeout handling
    try:
        if not pg.create_database():
            print('[ERROR] Failed to create database', flush=True)
            print('[ERROR] Check postgres/logfile for details', flush=True)
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print('[ERROR] Database creation timed out', flush=True)
        print('[ERROR] PostgreSQL may be unresponsive. Check postgres/logfile', flush=True)
        sys.exit(1)
    except Exception as e:
        print(f'[ERROR] Database creation failed: {e}', flush=True)
        sys.exit(1)

    print('[OK] PostgreSQL ready', flush=True)


if __name__ == '__main__':
    main()
