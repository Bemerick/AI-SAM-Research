# Testing Guide - Quick Setup Without Docker

Since Docker isn't available, we'll use your local PostgreSQL 17 installation.

## Step 1: Start PostgreSQL

PostgreSQL 17 is installed at `/Library/PostgreSQL/17/`. Let's find and start it:

### Option A: Using PostgreSQL.app (if installed)
If you have PostgreSQL.app, just open it and start the server.

### Option B: Using pg_ctl (command line)

```bash
# Find your PostgreSQL data directory
# Common locations:
# - /Library/PostgreSQL/17/data
# - ~/Library/Application Support/Postgres/var-17
# - /usr/local/var/postgres

# Start PostgreSQL (replace with your actual data directory)
/Library/PostgreSQL/17/bin/pg_ctl -D /Library/PostgreSQL/17/data start

# Or if using brew services:
brew services start postgresql@17
```

### Option C: Check if it's already running

```bash
ps aux | grep postgres
```

## Step 2: Create Database

```bash
# Connect to PostgreSQL
/Library/PostgreSQL/17/bin/psql -U postgres

# In psql, create the database:
CREATE DATABASE sam_govwin;

# Create user if needed:
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE sam_govwin TO postgres;

# Exit psql
\q
```

## Step 3: Configure Environment

Create `.env` file in the project root:

```bash
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research

# Copy example
cp .env.example .env
```

Edit `.env` and update `DATABASE_URL`:

```env
# For local PostgreSQL (adjust username/password as needed)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sam_govwin

# Your other keys
OPENAI_API_KEY=your_key_here
SAM_API_KEY=your_key_here
GOVWIN_USERNAME=your_username_here
GOVWIN_PASSWORD=your_password_here
```

## Step 4: Install Python Dependencies

```bash
# Make sure you're in the project root
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research

# Install backend dependencies
pip install -r backend/requirements.txt
```

## Step 5: Initialize Database

```bash
python backend/init_db.py
```

You should see:
```
✓ Database connection successful!
Creating database tables...
Database tables created successfully!
```

## Step 6: Start FastAPI Server

```bash
uvicorn backend.app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

## Step 7: Test API

Open your browser and go to:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Test with curl

```bash
# Health check
curl http://localhost:8000/health

# List SAM opportunities (will be empty initially)
curl http://localhost:8000/api/sam-opportunities

# Get analytics
curl http://localhost:8000/api/analytics/summary
```

## Step 8: Add Test Data (Optional)

Using the Swagger UI at http://localhost:8000/docs:

1. Click on **POST /api/sam-opportunities**
2. Click **"Try it out"**
3. Paste this test data:

```json
{
  "notice_id": "TEST001",
  "title": "Test AI Solutions Opportunity",
  "department": "Department of Agriculture",
  "standardized_department": "USDA",
  "naics_code": "541512",
  "fit_score": 8.5,
  "posted_date": "2024-01-15",
  "response_deadline": "2024-02-15",
  "solicitation_number": "SOL-2024-001",
  "description": "Seeking AI-powered data analysis solutions",
  "summary_description": "AI data analysis for agricultural research",
  "ptype": "Solicitation",
  "set_aside": "Small Business",
  "assigned_practice_area": "Business & Technology Services",
  "justification": "Strong alignment with AI capabilities",
  "review_for_bid": "Pending",
  "recommend_bid": "Pending",
  "sam_link": "https://sam.gov/opp/TEST001"
}
```

4. Click **Execute**
5. You should see a 201 response with the created opportunity

## Step 9: Test Frontend (When Ready)

```bash
cd frontend
npm run dev
```

Open http://localhost:5173

## Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Check what's on port 5432
lsof -i :5432

# Try connecting manually
/Library/PostgreSQL/17/bin/psql -U postgres -d sam_govwin
```

### Import Error in Python

```bash
# Make sure you're running from project root
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research

# Try with python path
PYTHONPATH=/Users/bob.emerick/dev/AI-projects/AI-SAM-Research python backend/init_db.py
```

### Port Already in Use

```bash
# If port 8000 is in use, use a different port
uvicorn backend.app.main:app --reload --port 8001
```

## Quick Commands Summary

```bash
# 1. Start PostgreSQL (if not running)
# Method varies based on installation

# 2. Initialize database
python backend/init_db.py

# 3. Start API
uvicorn backend.app.main:app --reload

# 4. Open browser
open http://localhost:8000/docs

# 5. Start frontend (when ready)
cd frontend && npm run dev
```
