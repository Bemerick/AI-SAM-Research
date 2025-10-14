#!/usr/bin/env python
"""
Database initialization script.
Creates all tables in the PostgreSQL database.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_db, drop_db, engine
from sqlalchemy import text


def check_database_connection():
    """Check if database connection is working."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Database connection successful!")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nMake sure PostgreSQL is running and DATABASE_URL is set correctly.")
        print("Expected format: postgresql://user:password@host:port/database")
        return False


def main():
    """Main initialization function."""
    print("=" * 60)
    print("SAM.gov + GovWin Database Initialization")
    print("=" * 60)

    # Check connection
    if not check_database_connection():
        return

    # Ask for confirmation if dropping tables
    response = input("\nDo you want to drop existing tables? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        print("\n⚠️  Dropping all tables...")
        drop_db()

    # Create tables
    print("\n📦 Creating database tables...")
    init_db()

    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    print("\nTables created:")
    print("  - sam_opportunities")
    print("  - govwin_opportunities")
    print("  - matches")
    print("  - search_logs")
    print("\nNext steps:")
    print("  1. Run analyze_opportunities.py to populate SAM opportunities")
    print("  2. Run search_govwin_matches.py to find GovWin matches")
    print("  3. Start the FastAPI server: uvicorn backend.app.main:app --reload")


if __name__ == "__main__":
    main()
