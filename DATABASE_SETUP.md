# Database Setup Guide

This guide explains how to set up the PostgreSQL database for the SAM.gov + GovWin matching system.

## Local Development Setup

### Prerequisites
- Docker installed on your machine
- Python 3.9+ installed

### Step 1: Start PostgreSQL with Docker

The easiest way to run PostgreSQL locally is using Docker Compose:

```bash
# Start PostgreSQL in the background
docker-compose up -d

# Check if it's running
docker-compose ps
```

This will start PostgreSQL on `localhost:5432` with:
- **Username**: `postgres`
- **Password**: `postgres`
- **Database**: `sam_govwin`

### Step 2: Install Python Dependencies

```bash
# Install backend dependencies
pip install -r backend/requirements.txt
```

### Step 3: Configure Environment Variables

Copy the example environment file and update it:

```bash
cp .env.example .env
```

Make sure the `DATABASE_URL` is set correctly in `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sam_govwin
```

### Step 4: Initialize the Database

Run the database initialization script:

```bash
python backend/init_db.py
```

This will:
1. Check database connection
2. Optionally drop existing tables (if you answer 'yes')
3. Create all required tables:
   - `sam_opportunities`
   - `govwin_opportunities`
   - `matches`
   - `search_logs`

### Step 5: Verify Database

You can connect to the database to verify it was created:

```bash
# Using Docker
docker exec -it sam_govwin_db psql -U postgres -d sam_govwin

# Once connected, list tables
\dt

# Exit
\q
```

## Database Schema

### Tables

**sam_opportunities**
- Stores SAM.gov opportunities with fit scores
- Primary key: `id`
- Unique constraint on `notice_id`
- Indexed on: `notice_id`, `fit_score`, `naics_code`

**govwin_opportunities**
- Stores GovWin opportunities found through searches
- Primary key: `id`
- Unique constraint on `govwin_id`
- Indexed on: `govwin_id`

**matches**
- Links SAM and GovWin opportunities
- Stores AI match scores and user review status
- Primary key: `id`
- Foreign keys: `sam_opportunity_id`, `govwin_opportunity_id`
- Unique constraint: Prevents duplicate matches
- Indexed on: `status`, `ai_match_score`

**search_logs**
- Tracks all GovWin searches performed
- Useful for debugging and analytics
- Foreign key: `sam_opportunity_id`

## Production Deployment (Azure)

### Option 1: Azure Database for PostgreSQL Flexible Server (Recommended)

1. **Create PostgreSQL Server in Azure Portal**
   - Go to Azure Portal > Create Resource > Azure Database for PostgreSQL
   - Choose "Flexible Server"
   - Select region and pricing tier (Basic tier is fine to start)
   - Set admin username and password

2. **Configure Firewall**
   - Add your IP address
   - Allow Azure services access (for App Service)

3. **Get Connection String**
   - Format: `postgresql://username:password@servername.postgres.database.azure.com:5432/sam_govwin?sslmode=require`

4. **Update Environment Variable**
   - In Azure App Service > Configuration > Application Settings
   - Add: `DATABASE_URL` with your connection string

5. **Initialize Database**
   ```bash
   # From your local machine, pointing to Azure DB
   DATABASE_URL="your_azure_connection_string" python backend/init_db.py
   ```

### Option 2: Azure Container Apps with PostgreSQL

Similar to Option 1, but deploy both the app and database as containers.

### Security Best Practices for Production

1. **Use SSL/TLS**: Always include `?sslmode=require` in connection string
2. **VNet Integration**: Place database in a Virtual Network
3. **Azure AD Authentication**: Use Managed Identity instead of passwords
4. **Key Vault**: Store DATABASE_URL in Azure Key Vault
5. **Backups**: Enable automated backups (default in Azure)
6. **Monitoring**: Enable Azure Monitor and diagnostic logs

## Common Operations

### Reset Database
```bash
python backend/init_db.py
# Answer 'yes' to drop tables
```

### Connect to Database
```bash
# Local (Docker)
docker exec -it sam_govwin_db psql -U postgres -d sam_govwin

# Azure (using psql)
psql "postgresql://username@servername.postgres.database.azure.com:5432/sam_govwin?sslmode=require"
```

### Stop PostgreSQL (Local)
```bash
docker-compose down

# To also remove data volumes
docker-compose down -v
```

### View Logs
```bash
# Docker
docker-compose logs postgres

# Azure
# Use Azure Portal > Database > Logs
```

## Migrations (Future)

For schema changes in the future, we'll use Alembic:

```bash
# Initialize Alembic (one time)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Troubleshooting

### "Connection refused" error
- Make sure Docker is running: `docker-compose ps`
- Check if PostgreSQL is listening: `docker-compose logs postgres`

### "Authentication failed" error
- Verify username/password in DATABASE_URL
- Check .env file is loaded correctly

### Tables not created
- Check database connection first
- Look for error messages in init_db.py output
- Verify all models are imported in backend/app/models.py

### Performance issues
- Add indexes for frequently queried columns
- Use connection pooling (already configured in database.py)
- Consider upgrading Azure PostgreSQL tier

## Next Steps

After database setup:
1. ✅ Database is ready
2. Migrate existing SAM.gov data to database
3. Set up FastAPI backend
4. Build React frontend
5. Deploy to Azure
