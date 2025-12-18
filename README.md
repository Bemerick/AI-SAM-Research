# SAM.gov Opportunity Management System

A comprehensive system for discovering, analyzing, and managing SAM.gov opportunities with AI-powered scoring, GovWin matching, and Microsoft Dynamics 365 CRM integration.

## Overview

This application provides an intelligent pipeline for federal contract opportunities from SAM.gov. It automatically fetches opportunities, scores them using AI, matches them with historical GovWin data, and integrates with Microsoft Dynamics CRM for opportunity management.

## Key Features

### 🔍 Opportunity Discovery & Management
- **Automated SAM.gov Fetching**: Daily retrieval of opportunities from SAM.gov API
- **AI-Powered Fit Scoring**: OpenAI integration to score opportunities (0-10) based on your capabilities
- **Smart Filtering**: Filter by NAICS codes, departments, fit scores, and workflow status
- **Amendment Tracking**: Automatically tracks opportunity updates and amendments
- **Opportunity Following/Starring**: Mark important opportunities for easy tracking

### 🎯 GovWin Integration
- **Historical Contract Matching**: Automatically matches SAM opportunities with GovWin historical data
- **Multi-Strategy Matching**: Uses agency name, NAICS code, and title keywords
- **AI Match Validation**: OpenAI validates match quality and provides reasoning
- **Contract History**: View related past contracts for each opportunity

### 📧 Email Sharing with Outlook Integration
- **Rich HTML Emails**: Share opportunities via beautifully formatted emails
- **Outlook Directory Search**: Real-time people lookup from your organization directory
- **Autocomplete Recipients**: Type-ahead email address suggestions
- **Personal Notes**: Add custom messages when sharing opportunities
- **File Attachments**: Attach documents to shared opportunities
- **Microsoft Graph API**: Seamless integration with Microsoft 365

### 🔄 Microsoft Dynamics 365 CRM Integration
- **One-Click Export**: Send opportunities to Dynamics CRM with a single click
- **Automatic Field Mapping**: Maps SAM data to CRM opportunity fields
- **Standard Field Support**: Uses native Dynamics 365 Sales fields
- **OAuth Authentication**: Secure authentication via Azure AD
- **Real-time Sync**: Immediately creates opportunities in your CRM

### 📊 Workflow Management
- **Review Status**: Track review decisions (Pending, Yes, No)
- **Bid Recommendations**: Record bid/no-bid recommendations
- **Review Comments**: Add notes and comments to opportunities
- **Practice Area Assignment**: Assign opportunities to practice areas
- **Tabbed Interface**: Separate views for opportunities and notices

### 🤖 AI-Powered Features
- **Fit Analysis**: AI generates justification for fit scores
- **Summary Generation**: Automatic opportunity summaries
- **Match Reasoning**: AI explains why GovWin contracts match SAM opportunities
- **Practice Area Suggestions**: AI recommends practice area assignments

## Architecture

### Backend (Python/FastAPI)
- **FastAPI** RESTful API with automatic OpenAPI documentation
- **SQLAlchemy** ORM with PostgreSQL/SQL Server support
- **Microsoft Graph API** for email and directory services
- **MSAL** for Azure AD authentication
- **OpenAI API** for AI scoring and analysis
- **Azure Functions** for scheduled tasks

### Frontend (React/TypeScript)
- **React 18** with TypeScript
- **TanStack Query** for data fetching and caching
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Vite** for fast development builds

### Integrations
- **SAM.gov API**: Opportunity data source
- **GovWin API**: Historical contract data
- **Microsoft Graph API**: Email and people search
- **Microsoft Dynamics 365**: CRM integration
- **OpenAI API**: AI scoring and analysis

## Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL or SQL Server
- Azure AD tenant (for Microsoft integrations)
- API keys for SAM.gov, OpenAI, and GovWin

### Backend Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd AI-SAM-Research
```

2. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Create `.env` file (see `.env.example`):
```bash
# SAM.gov Configuration
SAM_API_KEY=your_sam_api_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sam_govwin

# Microsoft Graph (for email and people search)
MS_TENANT_ID=your_tenant_id
MS_CLIENT_ID=your_client_id
MS_CLIENT_SECRET=your_client_secret

# Email Service
EMAIL_FROM_ADDRESS=info@yourcompany.com
EMAIL_FROM_NAME=SAM Opportunity System

# Microsoft Dynamics CRM (optional)
DYNAMICS_TENANT_ID=your_tenant_id
DYNAMICS_CLIENT_ID=your_client_id
DYNAMICS_CLIENT_SECRET=your_client_secret
DYNAMICS_RESOURCE_URL=https://yourorg.crm.dynamics.com

# GovWin API
GOVWIN_CLIENT_ID=your_client_id
GOVWIN_CLIENT_SECRET=your_client_secret
GOVWIN_USERNAME=your_username
GOVWIN_PASSWORD=your_password

# Frontend URL (for email links)
FRONTEND_URL=https://your-frontend-url.com
```

4. Initialize the database:
```bash
python init_db.py
```

5. Start the backend server:
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env` file:
```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

3. Start the development server:
```bash
npm run dev
```

4. Access the application at http://localhost:5173

## Configuration Guides

### Microsoft Dynamics CRM Setup
See [CRM_SETUP_GUIDE.md](CRM_SETUP_GUIDE.md) for detailed instructions on:
- Azure AD app registration
- CRM permissions configuration
- Application user setup
- Field mapping customization

### Email Service Setup
The email service uses Microsoft Graph API to send emails and search the organization directory:

1. **Azure AD App Registration**:
   - Register an app in Azure AD
   - Add API permissions: `Mail.Send`, `User.Read.All`
   - Grant admin consent

2. **Configure Environment Variables**:
   - Set `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`
   - Set `EMAIL_FROM_ADDRESS` and `EMAIL_FROM_NAME`

3. **Test Email Functionality**:
   - Open an opportunity detail page
   - Click "Share" button
   - Start typing recipient names to see directory search in action

## Usage

### Daily Operations

1. **View Opportunities**: Browse all opportunities on the home page
2. **Filter & Sort**: Use filters for NAICS, departments, fit scores
3. **Review Opportunities**:
   - Click on an opportunity to view details
   - Review AI fit score and justification
   - Check GovWin matches and historical contracts
   - Update workflow status (review/recommend)
4. **Share Opportunities**:
   - Click "Share" button
   - Use autocomplete to find recipients
   - Add personal notes and attachments
   - Send formatted email
5. **Send to CRM**:
   - Click "Send to CRM" button
   - Opportunity is created in Dynamics 365
   - View in CRM to continue sales process

### Automated Tasks

- **SAM Fetcher**: Runs daily to fetch new opportunities
- **AI Analyzer**: Scores opportunities and generates summaries
- **GovWin Matcher**: Searches for historical contract matches
- **Amendment Tracker**: Monitors for opportunity updates

## API Documentation

When running the backend server, access interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

**Opportunities**:
- `GET /api/sam-opportunities/` - List all opportunities
- `GET /api/sam-opportunities/{id}` - Get opportunity details
- `GET /api/sam-opportunities/{id}/matches` - Get GovWin matches
- `POST /api/sam-opportunities/{id}/share` - Share via email
- `POST /api/sam-opportunities/{id}/toggle-follow` - Follow/unfollow
- `PATCH /api/sam-opportunities/{id}` - Update workflow status

**Email & Directory**:
- `GET /api/sam-opportunities/search-people` - Search organization directory
- `POST /api/sam-opportunities/{id}/share` - Send email with attachments

**CRM Integration**:
- `POST /api/crm/opportunities/{id}/send` - Send to Dynamics CRM
- `GET /api/crm/opportunities/{id}/status` - Check CRM sync status

**Matches**:
- `GET /api/matches/` - List all matches
- `GET /api/matches/{id}` - Get match details
- `PATCH /api/matches/{id}` - Update match status

## Development

### Running Tests
```bash
cd backend
pytest
```

### CRM Schema Inspector
Test your Dynamics CRM connection and view available fields:
```bash
cd backend
python test_crm_schema.py
```

### Database Migrations
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Deployment

### Render.com (Current Deployment)
The application is deployed on Render with:
- Backend: Python web service
- Frontend: Static site
- Database: PostgreSQL

**Important**: Environment variables must be set in the Render dashboard, not in `.env` files.

### Azure Functions
Scheduled tasks run as Azure Functions:
- `SAMFetcher`: Daily opportunity fetching
- `AIAnalyzer`: AI scoring and analysis
- `GovWinMatcher`: Historical contract matching

## Troubleshooting

### CRM Integration Issues

**Mock Mode Message**:
- Verify all `DYNAMICS_*` environment variables are set
- Check Azure AD app has correct permissions
- Ensure application user exists in CRM

**Field Mapping Errors**:
- Run `python backend/test_crm_schema.py` to inspect your CRM schema
- Update `dynamics_client.py` field mappings to match your CRM
- Custom fields require publisher prefix (e.g., `cr7f3_fieldname`)

### Email Sharing Issues

**Directory Search Not Working**:
- Verify `MS_*` credentials are configured
- Check Azure AD app has `User.Read.All` permission
- Grant admin consent for the permission

**Email Not Sending**:
- Verify `EMAIL_FROM_ADDRESS` matches an actual mailbox
- Check Azure AD app has `Mail.Send` permission
- Ensure app has Send As permissions for the mailbox

## Recent Updates

### December 2024 Session
- ✅ Added notes/comments field to email sharing
- ✅ Added file attachment support for shared emails
- ✅ Implemented Microsoft Graph directory search for recipient autocomplete
- ✅ Created full Dynamics 365 CRM integration modules
- ✅ Fixed CRM field mappings to use standard Dynamics fields
- ✅ Added CRM schema inspector tool
- ✅ Fixed email button text visibility
- ✅ Added `msal` dependency for CRM authentication

## Support & Documentation

- **CRM Setup**: See [CRM_SETUP_GUIDE.md](CRM_SETUP_GUIDE.md)
- **API Docs**: http://localhost:8000/docs (when running)
- **Issues**: Report bugs and feature requests on GitHub

## License

MIT

## Credits

Built with:
- FastAPI
- React
- Microsoft Graph API
- OpenAI API
- GovWin API
- SAM.gov API
