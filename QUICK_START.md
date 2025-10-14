# 🚀 Quick Start Guide

## System is Ready!

Both backend and frontend are now running successfully.

## Access Your Application

### Frontend (Web Interface)
**URL:** http://localhost:5175

Open this in your browser to:
- View SAM.gov opportunities in grid layout
- Filter by fit score, department, NAICS
- Review opportunities (Review For Bid, Recommend Bid)
- View GovWin matches (when available)

### Backend (API)
**URL:** http://localhost:8000
**API Docs:** http://localhost:8000/docs

## What You Can Do Right Now

### 1. View Opportunities
- Open http://localhost:5175
- You'll see your test opportunity (TEST001) in a grid card
- Fit score: 8.5 (green badge = high priority)

### 2. View Details
- Click on the opportunity card
- See full description, deadlines, agency info
- View AI justification for fit score

### 3. Update Workflow
- On the detail page, scroll to "Workflow Review"
- Change **Review For Bid** from "Pending" to "Yes"
- Change **Recommend Bid** from "Pending" to "Yes"
- Add comments: "Excellent opportunity for our AI practice"
- Click **"Save Review"**
- ✅ Should see "Saved successfully!"

### 4. Test Navigation
- Click **"High Scoring"** in the top nav
- See opportunities with fit score ≥ 6
- Click **"Match Review"** (will be empty until GovWin integration)

### 5. Test Filters
- Go back to "All Opportunities"
- Use the filter bar:
  - Min Fit Score: 8
  - Click "Apply Filters"
  - Should still see TEST001

## Servers Running

| Service | URL | Status |
|---------|-----|--------|
| Frontend | http://localhost:5175 | ✅ Running |
| Backend API | http://localhost:8000 | ✅ Running |
| PostgreSQL | localhost:5432 | ✅ Running |

## Test Data Loaded

- **1 SAM Opportunity** (TEST001)
- **Title:** AI Solutions for Agricultural Data Analysis
- **Department:** Department of Agriculture
- **Fit Score:** 8.5
- **NAICS:** 541512
- **Deadline:** 2024-12-15

## Features Working

### Grid View ✅
- Responsive layout (1-4 columns)
- Color-coded fit scores
- Deadline urgency indicators
- Compact card design

### Opportunity Detail ✅
- Complete information display
- Workflow controls
- AI justification
- Link to SAM.gov

### Workflow Management ✅
- Review For Bid (Pending/Yes/No)
- Recommend Bid (Pending/Yes/No)
- Review Comments
- Auto-saves reviewer and timestamp

### Filtering ✅
- Fit score range
- Department search
- NAICS code
- Review status

## Stop/Start Servers

### Stop All Servers
```bash
# Find and kill processes
ps aux | grep uvicorn  # Backend
ps aux | grep vite     # Frontend

# Kill by PID
kill <PID>
```

### Start Backend
```bash
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Start Frontend
```bash
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research/frontend
npm run dev
```

## Add More Test Data

Use the API docs at http://localhost:8000/docs:

1. Go to **POST /api/sam-opportunities/**
2. Click **"Try it out"**
3. Paste this JSON and modify as needed:

```json
{
  "notice_id": "TEST002",
  "title": "Cloud Infrastructure Management Services",
  "department": "Department of Transportation",
  "standardized_department": "DOT",
  "naics_code": "541519",
  "fit_score": 7.2,
  "posted_date": "2024-01-20",
  "response_deadline": "2024-11-30",
  "solicitation_number": "DOT-2024-002",
  "description": "Seeking cloud infrastructure management and DevOps services.",
  "summary_description": "Cloud infrastructure and DevOps support",
  "ptype": "Solicitation",
  "set_aside": "Small Business",
  "assigned_practice_area": "Business & Technology Services",
  "justification": "Strong alignment with cloud and infrastructure capabilities.",
  "review_for_bid": "Pending",
  "recommend_bid": "Pending",
  "sam_link": "https://sam.gov/opp/TEST002"
}
```

4. Click **Execute**
5. Refresh frontend - new opportunity appears!

## Troubleshooting

### Frontend Shows Blank Page
1. Check browser console (F12)
2. Verify backend is running: http://localhost:8000/health
3. Check .env file in frontend folder

### "Network Error" in Frontend
1. Backend might not be running
2. Check CORS settings (should be enabled)
3. Verify API URL in frontend/.env

### Database Connection Error
1. Check PostgreSQL is running: `ps aux | grep postgres`
2. Verify DATABASE_URL in .env
3. Test connection: `psql -U postgres -d sam_govwin`

## What's Next

### Immediate (Working Now)
- ✅ View opportunities in grid
- ✅ Filter and search
- ✅ Update workflow fields
- ✅ Navigate between pages

### Coming Soon
- 🔄 GovWin integration (automatic search)
- 🤖 AI match evaluation
- 📊 Analytics dashboard
- 📧 Email notifications
- 👥 User authentication

## Documentation

- **ARCHITECTURE.md** - Full system architecture
- **IMPLEMENTATION_STATUS.md** - Progress tracking
- **DATABASE_SETUP.md** - Database configuration
- **TESTING_SUCCESS.md** - Backend test results
- **FRONTEND_COMPLETE.md** - Frontend features
- **QUICK_START.md** - This file

## Support

If you encounter issues:
1. Check the relevant .md documentation files
2. Check browser console for errors
3. Check server logs in terminal
4. Verify all services are running

## Enjoy! 🎉

You now have a fully functional opportunity management system running locally!

Open **http://localhost:5175** to get started.
