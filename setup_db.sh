#!/bin/bash
# Database setup script

echo "==================================================================="
echo "SAM.gov + GovWin Database Setup"
echo "==================================================================="
echo ""

# Check if database exists
echo "Checking if sam_govwin database exists..."
DB_EXISTS=$(/Library/PostgreSQL/17/bin/psql -U postgres -h localhost -tAc "SELECT 1 FROM pg_database WHERE datname='sam_govwin'")

if [ "$DB_EXISTS" = "1" ]; then
    echo "✓ Database 'sam_govwin' already exists"
else
    echo "Creating database 'sam_govwin'..."
    /Library/PostgreSQL/17/bin/psql -U postgres -h localhost -c "CREATE DATABASE sam_govwin;"

    if [ $? -eq 0 ]; then
        echo "✓ Database created successfully"
    else
        echo "✗ Failed to create database"
        exit 1
    fi
fi

echo ""
echo "Database setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with DATABASE_URL"
echo "2. Run: pip install -r backend/requirements.txt"
echo "3. Run: python backend/init_db.py"
echo "4. Run: uvicorn backend.app.main:app --reload"
