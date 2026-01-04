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


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    from postgres_manager import PostgreSQLManager

    pg = PostgreSQLManager()

    print('[INFO] Starting PostgreSQL...', flush=True)
    if not pg.start():
        print('[ERROR] PostgreSQL startup failed', flush=True)
        sys.exit(1)

    print('[INFO] Creating database...', flush=True)
    try:
        if not pg.create_database():
            print('[ERROR] Database creation failed', flush=True)
            pg.stop()
            sys.exit(1)
    except Exception as e:
        print(f'[ERROR] Database creation error: {e}', flush=True)
        pg.stop()
        sys.exit(1)

    print('[OK] PostgreSQL ready', flush=True)
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
