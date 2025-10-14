# Manual Setup Steps

Since we need the PostgreSQL password, here are the manual steps to complete the setup:

## Step 1: Create Database

Open a new terminal and run:

```bash
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research

# Run the setup script (it will ask for your postgres password)
./setup_db.sh
```

**OR manually:**

```bash
# Connect to PostgreSQL (will prompt for password)
/Library/PostgreSQL/17/bin/psql -U postgres -h localhost

# In the psql prompt, run:
CREATE DATABASE sam_govwin;
\q
```

## Step 2: Update .env File

```bash
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research

# Copy the example if you haven't already
cp .env.example .env

# Edit the .env file
nano .env
```

Update the `DATABASE_URL` line (replace `YOUR_PASSWORD` with your postgres password):

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/sam_govwin
```

Save and exit (Ctrl+X, then Y, then Enter)

## Step 3: Install Python Dependencies

```bash
# Make sure you're in the project root
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research

# Install dependencies
pip install -r backend/requirements.txt
```

## Step 4: Initialize Database

```bash
python backend/init_db.py
```

You should see:
```
==============================================================
SAM.gov + GovWin Database Initialization
==============================================================

✓ Database connection successful!

📦 Creating database tables...
Database tables created successfully!

==============================================================
✅ Database initialization complete!
==============================================================
```

## Step 5: Start FastAPI Server

```bash
uvicorn backend.app.main:app --reload
```

You should see:
```
INFO:     Will watch for changes in these directories: ['/Users/bob.emerick/dev/AI-projects/AI-SAM-Research']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Step 6: Test the API

**Open your browser:**
- http://localhost:8000/docs (Interactive API docs)
- http://localhost:8000/health (Health check)

**Test with curl:**

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy"}

# List opportunities (should be empty)
curl http://localhost:8000/api/sam-opportunities

# Expected response:
# []

# Get analytics
curl http://localhost:8000/api/analytics/summary

# Expected response:
# {"total_sam_opportunities":0,"total_govwin_opportunities":0,"high_scoring_sam_opps":0,"avg_fit_score":null,"total_searches_performed":0}
```

## Step 7: Add Test Data

Go to http://localhost:8000/docs and:

1. Find **POST /api/sam-opportunities**
2. Click **"Try it out"**
3. Paste this JSON:

```json
{
  "notice_id": "TEST001",
  "title": "AI Solutions for Agricultural Data Analysis",
  "department": "Department of Agriculture",
  "standardized_department": "USDA",
  "naics_code": "541512",
  "fit_score": 8.5,
  "posted_date": "2024-01-15",
  "response_deadline": "2024-02-15",
  "solicitation_number": "USDA-2024-001",
  "description": "The Department of Agriculture seeks AI-powered solutions for analyzing agricultural data to improve crop yield predictions and resource allocation.",
  "summary_description": "AI data analysis platform for agricultural research and decision support",
  "ptype": "Solicitation",
  "set_aside": "Small Business",
  "assigned_practice_area": "Business & Technology Services",
  "justification": "Strong alignment with AI and data analytics capabilities. Opportunity matches company expertise in government AI solutions.",
  "review_for_bid": "Pending",
  "recommend_bid": "Pending",
  "sam_link": "https://sam.gov/opp/TEST001"
}
```

4. Click **Execute**
5. You should get a **201 Created** response

## Step 8: Verify Data

Now test again:

```bash
# List opportunities (should show 1)
curl http://localhost:8000/api/sam-opportunities

# Get high-scoring opportunities
curl http://localhost:8000/api/sam-opportunities/high-scoring

# Get analytics
curl http://localhost:8000/api/analytics/summary
```

## Troubleshooting

### Can't find PostgreSQL password?

1. **Check your PostgreSQL installation notes** - The password was set during installation
2. **Reset the password:**
   ```bash
   # Stop PostgreSQL
   # Edit /Library/PostgreSQL/17/data/pg_hba.conf
   # Change "md5" to "trust" temporarily
   # Restart PostgreSQL
   # Connect without password: psql -U postgres
   # Set new password: ALTER USER postgres PASSWORD 'newpassword';
   # Change pg_hba.conf back to "md5"
   # Restart PostgreSQL
   ```

### Database connection fails

Check your DATABASE_URL in `.env`:
- Username should be `postgres`
- Host should be `localhost`
- Port should be `5432`
- Database name should be `sam_govwin`

### Import errors

Make sure you're running from the project root:
```bash
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research
python backend/init_db.py
```

## Next: Test Frontend

Once backend is working, test the frontend:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173
