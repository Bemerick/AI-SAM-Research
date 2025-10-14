"""
Script to fix date format from ISO (2025-10-10) to US (10/10/2025)
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sam_govwin")

# Create engine
engine = create_engine(DATABASE_URL)

# Update dates
with engine.connect() as conn:
    # Update posted_date from ISO to US format
    result = conn.execute(text("""
        UPDATE sam_opportunities
        SET posted_date = '10/10/2025'
        WHERE posted_date = '2025-10-10'
    """))
    conn.commit()

    print(f"✓ Updated {result.rowcount} posted_date fields from '2025-10-10' to '10/10/2025'")

    # Check the updated records
    result = conn.execute(text("""
        SELECT COUNT(*) as count
        FROM sam_opportunities
        WHERE posted_date = '10/10/2025'
    """))
    count = result.fetchone()[0]
    print(f"✓ Verified: {count} opportunities now have posted_date = '10/10/2025'")

print("\nDate format fix complete! The frontend should now show the opportunities.")
