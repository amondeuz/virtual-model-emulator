"""Start and monitor PostgreSQL server."""
import subprocess
import sys
import time
import signal

from postgres_manager import PostgreSQLManager

shutdown_requested = False


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    print(f'\n[INFO] Received shutdown signal {sig}', flush=True)
    shutdown_requested = True


def main():
    """Start PostgreSQL and monitor it continuously."""
    global shutdown_requested

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    pg = PostgreSQLManager()

    print('[INFO] Starting PostgreSQL server...', flush=True)
    if not pg.start():
        print('[ERROR] Failed to start PostgreSQL', flush=True)
        sys.exit(1)

    try:
        if not pg.create_database():
            print('[ERROR] Failed to create database', flush=True)
            print('[ERROR] Check postgres/logfile for details', flush=True)
            pg.stop()
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print('[ERROR] Database creation timed out', flush=True)
        pg.stop()
        sys.exit(1)
    except Exception as e:
        print(f'[ERROR] Database creation failed: {e}', flush=True)
        pg.stop()
        sys.exit(1)

    print('[OK] PostgreSQL ready', flush=True)
    print('[INFO] Entering monitoring mode - will stay running', flush=True)

    # Monitor loop - DO NOT EXIT
    try:
        while not shutdown_requested:
            if not pg.is_running():
                print('[ERROR] PostgreSQL has stopped unexpectedly!', flush=True)
                break

            # Check for shutdown signal every 100ms
            for _ in range(10):
                if shutdown_requested:
                    break
                time.sleep(0.1)

    except KeyboardInterrupt:
        print('\n[INFO] Shutdown signal received', flush=True)
    except Exception as e:
        print(f'[ERROR] Monitoring error: {e}', flush=True)
    finally:
        if pg.is_running():
            print('[INFO] Stopping PostgreSQL...', flush=True)
            pg.stop()
        print('[INFO] PostgreSQL exiting', flush=True)


if __name__ == '__main__':
    main()
