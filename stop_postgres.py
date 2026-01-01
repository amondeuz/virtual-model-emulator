"""Stop PostgreSQL gracefully."""
import subprocess
import sys

from postgres_config import PG_CTL, DATA_DIR


def stop_postgres():
    """Stop PostgreSQL server gracefully."""
    print('[INFO] Stopping PostgreSQL...', flush=True)

    try:
        result = subprocess.run([
            str(PG_CTL), 'stop',
            '-D', str(DATA_DIR),
            '-m', 'fast'  # Fast shutdown (waits for connections to close)
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print('[OK] PostgreSQL stopped', flush=True)
            return True
        elif 'not running' in result.stderr.lower() or 'not running' in result.stdout.lower():
            print('[OK] PostgreSQL was not running', flush=True)
            return True
        else:
            print(f'[WARN] Stop returned code {result.returncode}: {result.stderr}', flush=True)
            return False

    except subprocess.TimeoutExpired:
        print('[ERROR] PostgreSQL stop timed out', flush=True)
        # Try immediate shutdown as fallback
        try:
            subprocess.run([
                str(PG_CTL), 'stop',
                '-D', str(DATA_DIR),
                '-m', 'immediate'
            ], capture_output=True, text=True, timeout=10)
            print('[WARN] PostgreSQL stopped with immediate shutdown', flush=True)
            return True
        except Exception:
            pass
        return False
    except Exception as e:
        print(f'[ERROR] Failed to stop: {e}', flush=True)
        return False


def main():
    """Main entry point."""
    if not stop_postgres():
        sys.exit(1)


if __name__ == '__main__':
    main()
