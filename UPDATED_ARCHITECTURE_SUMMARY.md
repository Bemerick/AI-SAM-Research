# Updated Architecture Summary

## What Changed

### Original Plan
- SharePoint as primary data store
- Separate tools for SAM and GovWin
- Manual matching review process

### New Unified System
✅ **PostgreSQL database** replaces SharePoint
✅ **Single web interface** for both SAM opportunities and GovWin matches
✅ **Automatic GovWin matching** for high-scoring opportunities (fit_score >= 6)
✅ **Workflow fields** integrated into database (Review For Bid, Recommend Bid, Review Comments)

## User Experience

### View All SAM Opportunities
Users can now view all SAM.gov opportunities in a modern web interface with:
- **List view** with sortable columns
- **Filters**: Fit score, agency, NAICS, date range, review status
- **Search**: Full-text search across titles and descriptions
- **Detail view**: Click any opportunity to see complete details
- **Workflow actions**:
  - Review For Bid: Pending → Yes/No
  - Recommend Bid: Pending → Yes/No
  - Review Comments: Free text field
- **Visual indicators**:
  - Color-coded fit scores (green >= 6, yellow 4-6, red < 4)
  - "Has Matches" badge for opportunities with GovWin matches

### High-Scoring Opportunities (Fit Score >= 6)
- **Automatic GovWin search** runs when fit_score >= 6
- **"View Matches" button** shows GovWin opportunities
- **Integrated view**: SAM opportunity context + matched GovWin opportunities

### Match Review Interface
- **SAM opportunity shown at top** for context
- **GovWin matches listed below** with AI match scores
- **Side-by-side comparison** view
- **Actions per match**:
  - Confirm (this is a good match)
  - Reject (not a match)
  - Needs Info (requires more research)
  - Add notes

## Data Flow

```
1. SAM.gov API
   ↓
2. analyze_opportunities.py (AI scoring)
   ↓
3. PostgreSQL database (sam_opportunities table)
   ↓
4. [IF fit_score >= 6] → Auto GovWin search
   ↓
5. GovWin API search (multiple strategies)
   ↓
6. PostgreSQL (govwin_opportunities + matches tables)
   ↓
7. AI match evaluation (OpenAI)
   ↓
8. PostgreSQL (match scores updated)
   ↓
9. Web UI (React)
   ↓
10. User reviews and updates workflow fields
   ↓
11. PostgreSQL (review_for_bid, recommend_bid, review_comments)
```

## SharePoint Replacement Mapping

| SharePoint Column | Database Column | Type | Notes |
|-------------------|-----------------|------|-------|
| Title | title | TEXT | Opportunity title |
| NoticeID | notice_id | VARCHAR(255) | Unique identifier |
| DepartmentName | standardized_department | VARCHAR(255) | Standardized agency name |
| PostedDate | posted_date | VARCHAR(50) | Date posted |
| ResponseDate | response_deadline | VARCHAR(50) | Deadline |
| SetAside | set_aside | VARCHAR(100) | Set-aside type |
| Ptype | ptype | VARCHAR(100) | Procurement type |
| FitScore | fit_score | FLOAT | AI fit score (0-10) |
| Justification | justification | TEXT | AI justification |
| SummaryDescription | summary_description | TEXT | AI summary |
| SAMLink | sam_link | TEXT | URL to SAM.gov |
| NAICS | naics_code | VARCHAR(10) | NAICS code |
| PracticeArea | assigned_practice_area | VARCHAR(255) | Practice area |
| SolicitationNumber | solicitation_number | VARCHAR(255) | Sol number |
| ClassificationCode | classification_code | VARCHAR(10) | PSC code |
| **Review For Bid** ⭐ | **review_for_bid** | VARCHAR(50) | Pending/Yes/No |
| **Recommend Bid** ⭐ | **recommend_bid** | VARCHAR(50) | Pending/Yes/No |
| **Review Comments** ⭐ | **review_comments** | TEXT | User notes |

⭐ = Workflow fields that users interact with

## React UI Components

### Page Structure
```
src/pages/
├── Dashboard.tsx              # Main SAM opportunities list
├── OpportunityDetail.tsx      # Single opportunity + matches
├── HighScoring.tsx            # Filter to fit_score >= 6
└── MatchReview.tsx            # All matches view

src/components/
├── OpportunityCard.tsx        # SAM opportunity card
├── OpportunityDetailPanel.tsx # Full SAM details
├── WorkflowControls.tsx       # Review For Bid, Recommend Bid, Comments
├── MatchList.tsx              # List of GovWin matches
├── MatchCard.tsx              # Single GovWin match
├── MatchComparison.tsx        # Side-by-side SAM vs GovWin
├── FitScoreBadge.tsx          # Visual fit score (color-coded)
├── FilterBar.tsx              # Search and filter controls
└── StatusBadge.tsx            # Match status indicator
```

### Key UI Features
1. **Color-coded fit scores**:
   - Green (6-10): High priority
   - Yellow (4-6): Medium priority
   - Red (0-4): Low priority

2. **Badges**:
   - "Has Matches" - opportunity has GovWin matches
   - Match count (e.g., "3 matches")
   - Review status (Pending/Reviewed)

3. **Filters**:
   - Fit score range slider
   - Agency multi-select
   - NAICS filter
   - Date range picker
   - Review status (All/Pending/Yes/No)
   - Has matches (toggle)

4. **Search**:
   - Full-text across title, description
   - Instant results

5. **Actions**:
   - Bulk actions (review multiple opportunities)
   - Export to CSV/Excel
   - Print view

## API Endpoints

### SAM Opportunities
```
GET    /api/sam-opportunities              # List with filters
GET    /api/sam-opportunities/:id          # Get details
POST   /api/sam-opportunities              # Create (from analysis)
PATCH  /api/sam-opportunities/:id          # Update workflow fields
DELETE /api/sam-opportunities/:id          # Delete

GET    /api/sam-opportunities/:id/matches  # Get matches for opportunity
```

### GovWin Opportunities
```
GET    /api/govwin-opportunities           # List
GET    /api/govwin-opportunities/:id       # Get details
```

### Matches
```
GET    /api/matches                        # List with filters
GET    /api/matches/:id                    # Get details
POST   /api/matches                        # Create match
PATCH  /api/matches/:id                    # Update (confirm/reject)
DELETE /api/matches/:id                    # Delete
```

### Triggers
```
POST   /api/search/govwin/:sam_id          # Manual trigger GovWin search
POST   /api/evaluate/matches/:sam_id       # Manual trigger AI evaluation
```

### Analytics
```
GET    /api/analytics/summary              # Overview stats
GET    /api/analytics/match-quality        # Match quality metrics
```

## Automatic Matching Logic

When a SAM opportunity is created or updated:

```python
if opportunity.fit_score >= 6:
    # 1. Search GovWin with multiple strategies
    matches = search_govwin_for_opportunity(opportunity)

    # 2. Save GovWin opportunities to database
    for govwin_opp in matches:
        save_govwin_opportunity(govwin_opp)
        create_match(sam_id, govwin_id, strategy)

    # 3. Evaluate matches with AI
    for match in matches:
        ai_score = evaluate_match_with_ai(sam_opp, govwin_opp)
        update_match(match_id, ai_score, reasoning)
```

## Next Implementation Steps

### Phase 1: Database ✅ COMPLETE
- [x] PostgreSQL setup
- [x] Models with workflow fields
- [x] Schemas
- [x] CRUD operations
- [x] Database initialization

### Phase 2: Backend API (Next)
- [ ] FastAPI setup
- [ ] SAM opportunity endpoints
- [ ] GovWin opportunity endpoints
- [ ] Match endpoints
- [ ] Workflow update endpoints
- [ ] Auto-trigger GovWin search on fit_score >= 6

### Phase 3: GovWin Integration
- [ ] Integrate existing govwin_client
- [ ] Implement search orchestrator
- [ ] Add automatic trigger logic
- [ ] Batch processing

### Phase 4: AI Match Evaluation
- [ ] Implement match evaluator service
- [ ] OpenAI integration
- [ ] Batch evaluation
- [ ] Score calculation

### Phase 5: React Frontend
- [ ] Project setup (Vite + TypeScript)
- [ ] Design system from Design_Principles.md
- [ ] SAM opportunities list page
- [ ] Opportunity detail page
- [ ] Workflow controls component
- [ ] Match review interface
- [ ] Filters and search

### Phase 6: Migration
- [ ] Migrate existing SAM data from JSON to DB
- [ ] Test workflow in production
- [ ] Deprecate SharePoint integration
- [ ] User training

## Benefits Summary

### For Users
✅ **Single interface** - No more switching between tools
✅ **Better workflow** - Review opportunities and matches in one place
✅ **Automatic matching** - No manual GovWin searches
✅ **AI assistance** - Match scores and reasoning
✅ **Better search/filter** - Find opportunities faster
✅ **Modern UI** - Clean, fast, responsive

### For Business
✅ **No SharePoint** - Reduce licensing costs
✅ **Better data** - PostgreSQL for analytics
✅ **Scalable** - Azure-ready architecture
✅ **Automated** - Less manual work
✅ **Trackable** - Full audit trail
✅ **Flexible** - Easy to add features
