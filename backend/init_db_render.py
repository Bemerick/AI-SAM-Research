#!/usr/bin/env python
"""
Non-interactive database initialization script for Render deployment.
Creates all tables in the PostgreSQL database without user prompts.
"""
import sys
import os
from pathlib import Path

# Add project root to path so we can import backend modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.database import init_db, engine
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
        return False


def main():
    """Main initialization function."""
    print("=" * 60)
    print("SAM.gov + GovWin Database Initialization (Render)")
    print("=" * 60)

    # Check connection
    if not check_database_connection():
        sys.exit(1)

    # Create tables (will not drop existing tables)
    print("\n📦 Creating database tables...")
    try:
        init_db()
        print("\n" + "=" * 60)
        print("✅ Database initialization complete!")
        print("=" * 60)
        print("\nTables created:")
        print("  - sam_opportunities")
        print("  - govwin_opportunities")
        print("  - govwin_contracts")
        print("  - matches")
        print("  - search_logs")
    except Exception as e:
        print(f"\n✗ Error creating tables: {e}")
        print("\nThis is OK if tables already exist.")


if __name__ == "__main__":
    main()
