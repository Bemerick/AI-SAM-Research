# GovWin Matching System Architecture

## Overview
This document outlines the architecture for the unified SAM.gov and GovWin opportunity management system. The system provides a web interface to view all SAM.gov opportunities (replacing SharePoint), automatically searches GovWin for matches on high-scoring opportunities (fit_score >= 6), uses AI to evaluate match quality, and provides an integrated user interface for reviewing both opportunities and matches.

**Key Changes from Original Workflow:**
- ✅ **Database replaces SharePoint** as the primary data store
- ✅ **Unified web UI** for viewing all SAM opportunities and their GovWin matches
- ✅ **Automatic GovWin matching** for opportunities with fit_score >= 6
- ✅ **Workflow fields** (Review For Bid, Recommend Bid, Review Comments) integrated into database

## Architecture Components

### 1. Database Layer (PostgreSQL)

**Why PostgreSQL:**
- Production-ready for Azure deployment
- Azure Database for PostgreSQL (managed service)
- Concurrent access support
- Built-in backups and high availability
- Better performance at scale

**Schema Design:**

```sql
-- SAM Opportunities (replaces SharePoint)
CREATE TABLE sam_opportunities (
    id SERIAL PRIMARY KEY,
    notice_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    department VARCHAR(255),
    standardized_department VARCHAR(255),  -- For agency matching
    sub_tier VARCHAR(255),
    office VARCHAR(255),
    naics_code VARCHAR(10),
    full_parent_path TEXT,
    fit_score FLOAT,
    posted_date VARCHAR(50),
    response_deadline VARCHAR(50),
    solicitation_number VARCHAR(255),
    description TEXT,
    summary_description TEXT,  -- AI-generated summary
    type VARCHAR(50),
    ptype VARCHAR(100),  -- Procurement type
    classification_code VARCHAR(10),
    set_aside VARCHAR(100),
    place_of_performance_city VARCHAR(100),
    place_of_performance_state VARCHAR(2),
    place_of_performance_zip VARCHAR(10),
    point_of_contact_email VARCHAR(255),
    point_of_contact_name VARCHAR(255),
    sam_link TEXT,  -- SAM.gov UI link
    assigned_practice_area VARCHAR(255),
    justification TEXT,  -- AI justification

    -- Workflow fields (from SharePoint)
    review_for_bid VARCHAR(50) DEFAULT 'Pending',  -- Pending, Yes, No
    recommend_bid VARCHAR(50) DEFAULT 'Pending',   -- Pending, Yes, No
    review_comments TEXT,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,

    analysis_data TEXT,  -- JSON - full SAM data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- GovWin Opportunities (from search results)
CREATE TABLE govwin_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    govwin_id TEXT UNIQUE NOT NULL,
    title TEXT,
    type TEXT,
    gov_entity TEXT,
    primary_naics TEXT,
    description TEXT,
    value REAL,
    post_date TEXT,
    raw_data TEXT, -- JSON - full GovWin data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Matches (relationship + AI scoring)
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sam_opportunity_id INTEGER NOT NULL,
    govwin_opportunity_id INTEGER NOT NULL,
    search_strategy TEXT NOT NULL, -- agency, naics, title_keywords, combined, etc.
    ai_match_score REAL, -- 0-100
    ai_reasoning TEXT,
    status TEXT DEFAULT 'pending_review', -- pending_review, confirmed, rejected, needs_info
    user_notes TEXT,
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sam_opportunity_id) REFERENCES sam_opportunities(id),
    FOREIGN KEY (govwin_opportunity_id) REFERENCES govwin_opportunities(id),
    UNIQUE(sam_opportunity_id, govwin_opportunity_id)
);

-- Search History (for analytics/debugging)
CREATE TABLE search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sam_opportunity_id INTEGER NOT NULL,
    search_params TEXT, -- JSON
    results_count INTEGER,
    search_strategy TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sam_opportunity_id) REFERENCES sam_opportunities(id)
);

-- Indexes for performance
CREATE INDEX idx_sam_notice_id ON sam_opportunities(notice_id);
CREATE INDEX idx_sam_fit_score ON sam_opportunities(fit_score DESC);
CREATE INDEX idx_govwin_id ON govwin_opportunities(govwin_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_score ON matches(ai_match_score DESC);
```

### 2. Workflow Architecture

```
┌─────────────────────────────────────────────────────┐
│  1. SAM.gov Analysis (ENHANCED)                     │
│  - analyze_opportunities.py                          │
│  - Fetch from SAM.gov API                            │
│  - Score opportunities by fit (AI)                   │
│  - Save to sam_opportunities table (replaces SharePoint) │
│  - Set review_for_bid/recommend_bid = "Pending"      │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  2. Auto GovWin Matching (NEW - Automatic)          │
│  - Triggered automatically for fit_score >= 6        │
│  - Search strategies:                                │
│    * Agency name keyword search                      │
│    * NAICS code search                               │
│    * Title keywords search                           │
│    * Agency + NAICS combined                         │
│    * Title keywords + NAICS                          │
│  - Store GovWin results in govwin_opportunities      │
│  - Create match records in matches table             │
│  - Log searches in search_logs                       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  3. AI Match Evaluation (NEW - Automatic)           │
│  - For each match, use OpenAI to:                    │
│    * Compare SAM vs GovWin descriptions              │
│    * Verify agency alignment                         │
│    * Check NAICS relevance                           │
│    * Assess scope overlap                            │
│    * Generate match score (0-100)                    │
│    * Provide reasoning                               │
│  - Update matches table with AI scores               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  4. Web UI - SAM Opportunities View (NEW)           │
│  - ALL SAM opportunities in clean interface          │
│  - Replaces SharePoint list                          │
│  - Features:                                         │
│    * List view with filters (fit score, agency, etc) │
│    * Detail view with full info                      │
│    * Workflow actions:                               │
│      - Review For Bid (Pending/Yes/No)               │
│      - Recommend Bid (Pending/Yes/No)                │
│      - Review Comments (text field)                  │
│    * Visual badges for high-scoring (fit >= 6)       │
│    * "Has Matches" indicator                         │
│    * Click to view GovWin matches (if any)           │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  5. Web UI - Integrated Match Review (NEW)          │
│  - Shows SAM opportunity at top (context)            │
│  - Lists GovWin matches below with AI scores         │
│  - Side-by-side comparison view                      │
│  - Actions:                                          │
│    * Confirm/Reject/Needs Info                       │
│    * Add match notes                                 │
│  - All in one unified interface                      │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  6. Notifications (OPTIONAL - Teams)                │
│  - Post high-value opportunities to Teams            │
│  - Post confirmed matches to Teams                   │
│  - Include SAM and GovWin links                      │
└─────────────────────────────────────────────────────┘
```

### 3. Technology Stack

**Backend:**
- Python 3.x
- SQLite + SQLAlchemy ORM
- FastAPI (REST API server)
- OpenAI API (match evaluation)
- Existing: SAM.gov client, GovWin client

**Frontend:**
- React 18+
- TypeScript
- Tailwind CSS (following Design_Principles.md)
- Axios/Fetch for API calls
- React Query for data management

**Development Tools:**
- Vite (React build tool)
- ESLint + Prettier
- SQLAlchemy migrations

### 4. Project File Structure

```
AI-SAM-Research/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py             # Enhanced with new DB models
│   │   ├── schemas.py            # Pydantic schemas for API
│   │   ├── crud.py               # Database operations
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── opportunities.py  # SAM endpoints
│   │   │   ├── govwin.py         # GovWin endpoints
│   │   │   └── matches.py        # Match management endpoints
│   │   ├── services/
│   │   │   ├── sam_client.py     # Existing SAM client
│   │   │   ├── govwin_client.py  # GovWin integration
│   │   │   ├── match_evaluator.py # AI matching logic
│   │   │   └── notifications.py  # Teams/SharePoint
│   │   └── main.py               # FastAPI app
│   ├── analyze_opportunities.py   # Enhanced to save to DB
│   ├── search_govwin_matches.py   # GovWin search orchestrator
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MatchCard.tsx
│   │   │   ├── OpportunityDetail.tsx
│   │   │   ├── MatchComparison.tsx
│   │   │   ├── FilterBar.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── MatchReview.tsx
│   │   │   └── Analytics.tsx
│   │   ├── services/
│   │   │   └── api.ts            # API client
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript types
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── sam_govwin.db                  # SQLite database
├── ARCHITECTURE.md                # This file
├── Design_Principles.md           # UI/UX guidelines
└── README.md
```

### 5. Implementation Phases

#### Phase 1: Database Foundation
**Goal:** Set up database infrastructure and migrate existing data
- [ ] Create database models using SQLAlchemy
- [ ] Set up database initialization script
- [ ] Create migration for schema
- [ ] Modify `analyze_opportunities.py` to save to DB
- [ ] Create CRUD operations for all tables
- **Deliverable:** Working database with SAM opportunities

#### Phase 2: Backend API
**Goal:** Build RESTful API for data access
- [ ] Set up FastAPI application
- [ ] Create endpoints for:
  - SAM opportunities (list, detail, filter)
  - GovWin opportunities (list, detail)
  - Matches (list, create, update, delete)
  - Statistics and analytics
- [ ] Add authentication (if needed)
- [ ] API documentation (auto-generated by FastAPI)
- **Deliverable:** Working REST API

#### Phase 3: GovWin Integration
**Goal:** Implement automated GovWin search and matching
- [ ] Build `govwin_integration.py` with search strategies
- [ ] Implement `search_govwin_matches.py` orchestrator
- [ ] Create batch processing for multiple SAM opportunities
- [ ] Store all results in database
- [ ] Add error handling and retry logic
- **Deliverable:** Automated GovWin search system

#### Phase 4: AI Match Evaluation
**Goal:** Use OpenAI to score and evaluate matches
- [ ] Implement `match_evaluator.py` service
- [ ] Design effective prompts for match evaluation
- [ ] Batch process matches to optimize API usage
- [ ] Store AI scores and reasoning in database
- [ ] Add quality metrics and monitoring
- **Deliverable:** AI-powered match scoring

#### Phase 5: React Frontend
**Goal:** Build user interface for match review
- [ ] Set up React + TypeScript + Vite project
- [ ] Implement design system from Design_Principles.md
- [ ] Build core components:
  - Dashboard with match list
  - Match comparison view
  - Filter and search interface
  - Status management controls
- [ ] Integrate with backend API
- [ ] Add responsive design
- **Deliverable:** Production-ready web UI

#### Phase 6: Enhanced Reporting
**Goal:** Improve notifications and reporting
- [ ] Enhance Teams notifications with match data
- [ ] Update SharePoint integration for confirmed matches
- [ ] Create analytics dashboard
- [ ] Add export functionality
- **Deliverable:** Complete reporting system

### 6. API Endpoints (Planned)

```
GET    /api/sam-opportunities          # List SAM opportunities
GET    /api/sam-opportunities/:id      # Get SAM opportunity details
POST   /api/sam-opportunities          # Create SAM opportunity
GET    /api/sam-opportunities/search   # Search SAM opportunities

GET    /api/govwin-opportunities       # List GovWin opportunities
GET    /api/govwin-opportunities/:id   # Get GovWin details

GET    /api/matches                    # List matches (with filters)
GET    /api/matches/:id                # Get match details
POST   /api/matches                    # Create match
PATCH  /api/matches/:id                # Update match (status, notes)
DELETE /api/matches/:id                # Delete match

POST   /api/search/govwin              # Trigger GovWin search
POST   /api/evaluate/matches           # Trigger AI evaluation

GET    /api/analytics/summary          # Get analytics summary
GET    /api/analytics/match-quality    # Get match quality metrics
```

### 7. Key Features

**Automated Matching:**
- Multiple search strategies (agency, NAICS, keywords)
- Configurable search parameters
- Batch processing support
- Deduplication of GovWin opportunities

**AI Evaluation:**
- GPT-4 powered match scoring
- Detailed reasoning and explanations
- Configurable evaluation criteria
- Quality metrics tracking

**User Review Interface:**
- Clean, intuitive React UI
- Side-by-side opportunity comparison
- Quick approve/reject actions
- Notes and collaboration support
- Filter and search capabilities
- Mobile-responsive design

**Integration:**
- Seamless integration with existing SAM.gov workflow
- Enhanced Teams notifications
- SharePoint list updates for confirmed matches
- Export to various formats

### 8. Design Principles Integration

The React UI will follow the principles outlined in `Design_Principles.md`:
- Clean, modern interface with clear hierarchy
- Consistent color scheme and typography
- Intuitive navigation and actions
- Responsive design for all screen sizes
- Accessible components (WCAG 2.1 AA)
- Performance optimized
- Progressive enhancement

### 9. Future Enhancements

**Machine Learning:**
- Train model on confirmed/rejected matches
- Improve search strategy selection
- Automated match confidence scoring

**Advanced Features:**
- Opportunity tracking and alerts
- Competitive intelligence
- Team collaboration tools
- Advanced analytics and reporting
- API integrations with other systems

**Scalability:**
- Option to migrate to PostgreSQL if needed
- Containerization with Docker
- Cloud deployment (AWS/Azure)
- CI/CD pipeline

## Next Steps

1. Review and approve architecture
2. Set up development environment
3. Begin Phase 1: Database Foundation
4. Iterate and refine based on feedback
