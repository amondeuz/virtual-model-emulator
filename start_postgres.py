"""Start PostgreSQL server before running the app."""
import sys

from postgres_manager import PostgreSQLManager


def main():
    """Main entry point."""
    pg = PostgreSQLManager()

    if not pg.start():
        sys.exit(1)

    pg.create_database()

    print('[OK] PostgreSQL ready', flush=True)


if __name__ == '__main__':
    main()
