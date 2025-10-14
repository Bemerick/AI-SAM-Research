# Backend API

FastAPI backend for SAM.gov and GovWin opportunity management system.

## Features

- RESTful API for SAM.gov opportunities
- GovWin opportunity management
- Match management and AI scoring
- Analytics and statistics
- PostgreSQL database integration
- CORS enabled for React frontend

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root (see `.env.example`):

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sam_govwin
OPENAI_API_KEY=your_key_here
SAM_API_KEY=your_key_here
```

### 3. Start PostgreSQL

```bash
docker-compose up -d
```

### 4. Initialize Database

```bash
python backend/init_db.py
```

### 5. Start API Server

```bash
# Development mode (auto-reload)
uvicorn backend.app.main:app --reload

# Or using the main.py directly
python backend/app/main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### SAM Opportunities

```
GET    /api/sam-opportunities              # List all (with filters)
GET    /api/sam-opportunities/high-scoring # List fit_score >= 6
GET    /api/sam-opportunities/{id}         # Get by ID
GET    /api/sam-opportunities/notice/{notice_id}  # Get by notice ID
POST   /api/sam-opportunities              # Create new
PATCH  /api/sam-opportunities/{id}         # Update (workflow fields)
DELETE /api/sam-opportunities/{id}         # Delete
GET    /api/sam-opportunities/{id}/matches # Get matches for opportunity
```

**Filters:**
- `skip`, `limit` - Pagination
- `min_fit_score` - Minimum fit score
- `department` - Filter by department
- `naics_code` - Filter by NAICS
- `review_for_bid` - Filter by review status
- `recommend_bid` - Filter by recommendation

### GovWin Opportunities

```
GET    /api/govwin-opportunities           # List all
GET    /api/govwin-opportunities/{id}      # Get by ID
GET    /api/govwin-opportunities/govwin-id/{govwin_id}  # Get by GovWin ID
POST   /api/govwin-opportunities           # Create new
DELETE /api/govwin-opportunities/{id}      # Delete
```

### Matches

```
GET    /api/matches                        # List all (with filters)
GET    /api/matches/pending                # List pending review
GET    /api/matches/{id}                   # Get by ID (with full details)
POST   /api/matches                        # Create new
PATCH  /api/matches/{id}                   # Update (confirm/reject)
DELETE /api/matches/{id}                   # Delete
```

**Filters:**
- `skip`, `limit` - Pagination
- `status` - pending_review, confirmed, rejected, needs_info
- `min_score`, `max_score` - AI match score range
- `search_strategy` - Filter by search strategy

### Analytics

```
GET    /api/analytics/summary              # Opportunity statistics
GET    /api/analytics/match-quality        # Match quality metrics
```

## Example API Calls

### List High-Scoring SAM Opportunities

```bash
curl http://localhost:8000/api/sam-opportunities/high-scoring
```

### Get SAM Opportunity with Matches

```bash
curl http://localhost:8000/api/sam-opportunities/1
curl http://localhost:8000/api/sam-opportunities/1/matches
```

### Update Workflow Fields

```bash
curl -X PATCH http://localhost:8000/api/sam-opportunities/1 \
  -H "Content-Type: application/json" \
  -d '{
    "review_for_bid": "Yes",
    "recommend_bid": "Yes",
    "review_comments": "Excellent fit for our practice area",
    "reviewed_by": "john.doe@company.com"
  }'
```

### Update Match Status

```bash
curl -X PATCH http://localhost:8000/api/matches/1 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "confirmed",
    "user_notes": "Good match - agency alignment confirmed",
    "reviewed_by": "john.doe@company.com"
  }'
```

### Get Analytics

```bash
curl http://localhost:8000/api/analytics/summary
curl http://localhost:8000/api/analytics/match-quality
```

## Response Examples

### SAM Opportunity Response

```json
{
  "id": 1,
  "notice_id": "abc123",
  "title": "AI Solutions for Data Analysis",
  "department": "Department of Agriculture",
  "fit_score": 8.5,
  "posted_date": "2024-01-15",
  "response_deadline": "2024-02-15",
  "naics_code": "541512",
  "assigned_practice_area": "Business & Technology Services",
  "justification": "Strong alignment with AI capabilities...",
  "review_for_bid": "Pending",
  "recommend_bid": "Pending",
  "review_comments": null,
  "reviewed_by": null,
  "reviewed_at": null,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": null
}
```

### Match with Details Response

```json
{
  "id": 1,
  "sam_opportunity_id": 1,
  "govwin_opportunity_id": 5,
  "search_strategy": "title_keywords",
  "ai_match_score": 85.5,
  "ai_reasoning": "Strong match based on similar scope and agency...",
  "status": "pending_review",
  "user_notes": null,
  "reviewed_by": null,
  "reviewed_at": null,
  "created_at": "2024-01-15T11:00:00Z",
  "sam_opportunity": { /* full SAM opportunity object */ },
  "govwin_opportunity": { /* full GovWin opportunity object */ }
}
```

## Development

### Run with Auto-Reload

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### View API Documentation

Open http://localhost:8000/docs in your browser for interactive API documentation.

### Database Migrations

For schema changes, we'll use Alembic (to be set up):

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Testing

### Manual Testing with Swagger UI

1. Start the server
2. Go to http://localhost:8000/docs
3. Try out endpoints interactively

### Using curl

See example API calls above.

### Using Python requests

```python
import requests

# Get high-scoring opportunities
response = requests.get("http://localhost:8000/api/sam-opportunities/high-scoring")
opportunities = response.json()

# Update workflow
response = requests.patch(
    "http://localhost:8000/api/sam-opportunities/1",
    json={
        "review_for_bid": "Yes",
        "recommend_bid": "Yes",
        "review_comments": "Great fit!"
    }
)
```

## Deployment

### Production Settings

Update `.env` for production:

```bash
# Azure Database for PostgreSQL
DATABASE_URL=postgresql://user:pass@server.postgres.database.azure.com:5432/sam_govwin?sslmode=require

# Frontend URL for CORS
FRONTEND_URL=https://your-frontend-domain.com
```

### Run in Production

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Database Connection Error

Make sure PostgreSQL is running:
```bash
docker-compose ps
```

### CORS Errors

Check that your frontend URL is in the `origins` list in `main.py`.

### Import Errors

Make sure you're running from the project root and the backend directory is in your Python path.
