# Database Migration Guide

## Running Migrations on Render

When deploying new code that adds database columns, you need to run the migration script on Render.

### Option 1: SSH into Render and Run Migration

1. Get shell access to your Render service:
   ```bash
   render shell <your-service-name>
   ```

2. Navigate to the backend directory and run the migration:
   ```bash
   cd backend
   python migrate_db.py
   ```

3. The script will:
   - Check if columns exist before adding them
   - Add missing columns: `is_amendment`, `original_notice_id`, `superseded_by_notice_id`, `is_followed`
   - Create indexes on new columns
   - Update existing records with default values

### Option 2: Add to Build Command

You can add the migration to your Render build command to run automatically on each deployment:

**Current build command:**
```bash
cd backend && pip install -r requirements.txt
```

**Updated build command with migration:**
```bash
cd backend && pip install -r requirements.txt && python migrate_db.py
```

This will run the migration automatically before each deployment. The script is safe to run multiple times.

### Option 3: Manual SQL (PostgreSQL on Render)

If you prefer to run SQL directly, connect to your PostgreSQL database and run:

```sql
-- Add amendment tracking columns
ALTER TABLE sam_opportunities ADD COLUMN IF NOT EXISTS is_amendment INTEGER DEFAULT 0;
ALTER TABLE sam_opportunities ADD COLUMN IF NOT EXISTS original_notice_id VARCHAR(255);
ALTER TABLE sam_opportunities ADD COLUMN IF NOT EXISTS superseded_by_notice_id VARCHAR(255);
ALTER TABLE sam_opportunities ADD COLUMN IF NOT EXISTS is_followed INTEGER DEFAULT 0;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_is_amendment ON sam_opportunities(is_amendment);
CREATE INDEX IF NOT EXISTS idx_original_notice_id ON sam_opportunities(original_notice_id);
CREATE INDEX IF NOT EXISTS idx_superseded_by_notice_id ON sam_opportunities(superseded_by_notice_id);
CREATE INDEX IF NOT EXISTS idx_is_followed ON sam_opportunities(is_followed);

-- Update existing records
UPDATE sam_opportunities
SET is_amendment = 0, is_followed = 0
WHERE is_amendment IS NULL OR is_followed IS NULL;
```

## Verifying the Migration

After running the migration, verify it worked:

```bash
python -c "
from app.database import SessionLocal
from sqlalchemy import inspect, text

db = SessionLocal()
inspector = inspect(db.get_bind())

print('Columns in sam_opportunities:')
for col in inspector.get_columns('sam_opportunities'):
    print(f\"  - {col['name']} ({col['type']})\")

# Check counts
result = db.execute(text('SELECT COUNT(*) FROM sam_opportunities')).scalar()
print(f'\nTotal opportunities: {result}')

followed = db.execute(text('SELECT COUNT(*) FROM sam_opportunities WHERE is_followed = 1')).scalar()
print(f'Followed: {followed}')

db.close()
"
```

## Recent Migrations

### 2025-11-14: Amendment Tracking & Follow Feature
- Added `is_amendment` (INTEGER, default 0, indexed)
- Added `original_notice_id` (VARCHAR(255), indexed)
- Added `superseded_by_notice_id` (VARCHAR(255), indexed)
- Added `is_followed` (INTEGER, default 0, indexed)

**Purpose:**
- Track amendments/updates to SAM opportunities
- Allow users to follow/star opportunities
- Show "Updated" and "Superseded" badges in UI
- Add "Followed" tab for starred opportunities
