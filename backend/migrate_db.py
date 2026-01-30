#!/usr/bin/env python3
"""
Database migration script for adding new columns to sam_opportunities table.
Safe to run multiple times - checks if columns exist before adding them.
Works with both PostgreSQL (Render) and SQL Server (Azure).
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine
from sqlalchemy import text, inspect

def column_exists(table_name: str, column_name: str, inspector) -> bool:
    """Check if a column exists in a table."""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def run_migration():
    """Run database migration to add new columns."""
    db = SessionLocal()
    inspector = inspect(engine)

    try:
        print("=" * 80)
        print("Starting database migration...")
        print("=" * 80)

        # Columns to add
        columns_to_add = [
            {
                'name': 'is_amendment',
                'definition': 'INTEGER DEFAULT 0',
                'index': 'CREATE INDEX idx_is_amendment ON sam_opportunities(is_amendment)'
            },
            {
                'name': 'original_notice_id',
                'definition': 'VARCHAR(255)',
                'index': 'CREATE INDEX idx_original_notice_id ON sam_opportunities(original_notice_id)'
            },
            {
                'name': 'superseded_by_notice_id',
                'definition': 'VARCHAR(255)',
                'index': 'CREATE INDEX idx_superseded_by_notice_id ON sam_opportunities(superseded_by_notice_id)'
            },
            {
                'name': 'is_followed',
                'definition': 'INTEGER DEFAULT 0',
                'index': 'CREATE INDEX idx_is_followed ON sam_opportunities(is_followed)'
            }
        ]

        # Column alterations
        columns_to_alter = [
            {
                'name': 'place_of_performance_state',
                'old_definition': 'VARCHAR(2)',
                'new_definition': 'VARCHAR(10)'
            }
        ]

        added_columns = []

        for col_info in columns_to_add:
            col_name = col_info['name']

            if column_exists('sam_opportunities', col_name, inspector):
                print(f"✓ Column '{col_name}' already exists, skipping...")
            else:
                print(f"Adding column '{col_name}'...")

                # Add column
                sql = f"ALTER TABLE sam_opportunities ADD COLUMN {col_name} {col_info['definition']}"
                db.execute(text(sql))
                db.commit()

                print(f"✓ Column '{col_name}' added successfully")
                added_columns.append(col_name)

                # Create index
                if col_info.get('index'):
                    try:
                        print(f"  Creating index for '{col_name}'...")
                        db.execute(text(col_info['index']))
                        db.commit()
                        print(f"  ✓ Index created")
                    except Exception as e:
                        print(f"  Note: Index creation failed or already exists: {e}")
                        db.rollback()

        # Alter columns
        for col_info in columns_to_alter:
            col_name = col_info['name']
            print(f"\nAltering column '{col_name}' from {col_info['old_definition']} to {col_info['new_definition']}...")

            try:
                # PostgreSQL syntax for column alteration
                sql = f"ALTER TABLE sam_opportunities ALTER COLUMN {col_name} TYPE {col_info['new_definition']}"
                db.execute(text(sql))
                db.commit()
                print(f"✓ Column '{col_name}' altered successfully")
            except Exception as e:
                print(f"Note: Column alteration failed or already altered: {e}")
                db.rollback()

        # Update NULL values to defaults for new columns
        if added_columns:
            print("\nUpdating default values for new columns...")

            if 'is_amendment' in added_columns or 'is_followed' in added_columns:
                update_sql = "UPDATE sam_opportunities SET "
                updates = []
                if 'is_amendment' in added_columns:
                    updates.append("is_amendment = 0")
                if 'is_followed' in added_columns:
                    updates.append("is_followed = 0")

                update_sql += ", ".join(updates)
                update_sql += " WHERE is_amendment IS NULL OR is_followed IS NULL"

                result = db.execute(text(update_sql))
                db.commit()
                print(f"✓ Updated {result.rowcount} rows with default values")

        print("\n" + "=" * 80)
        print("Migration completed successfully!")
        print("=" * 80)

        # Show summary
        print("\nColumn status:")
        inspector = inspect(engine)  # Refresh inspector
        for col_info in columns_to_add:
            exists = column_exists('sam_opportunities', col_info['name'], inspector)
            status = "✓ EXISTS" if exists else "✗ MISSING"
            print(f"  {status}: {col_info['name']}")

        return True

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
