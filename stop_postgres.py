"""Stop PostgreSQL gracefully."""
import sys

from postgres_manager import PostgreSQLManager


def main():
    """Main entry point."""
    pg = PostgreSQLManager()

    if not pg.stop():
        sys.exit(1)


if __name__ == '__main__':
    main()
