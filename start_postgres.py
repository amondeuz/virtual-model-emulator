"""Start and monitor PostgreSQL server."""
import subprocess
import sys
import time
import signal
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

shutdown_requested = False


def signal_handler(sig, frame):
    global shutdown_requested
    print(f'\n[INFO] Received signal {sig}', flush=True)
    shutdown_requested = True


def ensure_database_exists():
    """Direct method to ensure 'litellm' database exists.
    This is a fallback if postgres_manager.create_database() fails."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    max_retries = 10
    for i in range(max_retries):
        try:
            print(f'[INFO] Attempting to connect to PostgreSQL (attempt {i+1}/{max_retries})...', flush=True)
            # Try to connect to default 'postgres' database first
            conn = psycopg2.connect(
                host="localhost",
                port=5450,
                user="postgres",
                password="postgres",
                database="postgres"  # Connect to default DB first
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'litellm'")
            exists = cursor.fetchone()

            if not exists:
                print('[INFO] Creating "litellm" database...', flush=True)
                cursor.execute('CREATE DATABASE litellm')
                print('[OK] Database "litellm" created successfully', flush=True)
            else:
                print('[OK] Database "litellm" already exists', flush=True)

            # Close connections
            cursor.close()
            conn.close()
            return True

        except psycopg2.OperationalError as e:
            if "Connection refused" in str(e) or "the database system is starting up" in str(e):
                print(f'[INFO] PostgreSQL not ready yet, waiting...', flush=True)
                time.sleep(2)
            else:
                print(f'[ERROR] PostgreSQL connection error: {e}', flush=True)
                return False
        except Exception as e:
            print(f'[ERROR] Database creation failed: {e}', flush=True)
            import traceback
            traceback.print_exc()
            return False

    print('[ERROR] Failed to create database after max retries', flush=True)
    return False


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    from postgres_manager import PostgreSQLManager

    pg = PostgreSQLManager()

    print('[INFO] Starting PostgreSQL...', flush=True)
    if not pg.start():
        print('[ERROR] PostgreSQL startup failed', flush=True)
        sys.exit(1)

    print('[INFO] Waiting for PostgreSQL to be ready...', flush=True)
    time.sleep(3)  # Give PostgreSQL time to start

    # Try original method first
    print('[INFO] Attempting database creation via postgres_manager...', flush=True)
    try:
        if not pg.create_database():
            print('[WARN] postgres_manager.create_database() returned False, trying direct method...', flush=True)
            if not ensure_database_exists():
                print('[ERROR] Direct database creation also failed', flush=True)
                pg.stop()
                sys.exit(1)
    except Exception as e:
        print(f'[WARN] Database creation error in postgres_manager: {e}', flush=True)
        print('[INFO] Trying direct method...', flush=True)
        if not ensure_database_exists():
            print('[ERROR] Direct database creation failed', flush=True)
            pg.stop()
            sys.exit(1)

    print('[OK] PostgreSQL ready with "litellm" database', flush=True)
    print('[INFO] Entering monitoring mode...', flush=True)

    # Monitor until shutdown
    try:
        while not shutdown_requested:
            if not pg.is_running():
                print('[ERROR] PostgreSQL stopped unexpectedly', flush=True)
                break

            # Check for shutdown signal every 100ms
            for _ in range(10):
                if shutdown_requested:
                    break
                time.sleep(0.1)

    except KeyboardInterrupt:
        print('\n[INFO] Keyboard interrupt', flush=True)
    except Exception as e:
        print(f'[ERROR] Monitoring error: {e}', flush=True)
    finally:
        if pg.is_running():
            print('[INFO] Stopping PostgreSQL...', flush=True)
            pg.stop()
        print('[INFO] PostgreSQL service exiting', flush=True)


if __name__ == '__main__':
    main()
