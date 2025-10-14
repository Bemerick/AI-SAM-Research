"""
Main FastAPI application for SAM.gov and GovWin opportunity management.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.app.api import sam_opportunities, govwin_opportunities, matches, analytics, govwin_contracts, crm_integration

# Create FastAPI app
app = FastAPI(
    title="SAM.gov & GovWin Opportunity Management API",
    description="API for managing SAM.gov opportunities and GovWin matches",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for React frontend
# In production, replace "*" with your actual frontend domain
origins = [
    "http://localhost:3000",  # React default dev server
    "http://localhost:5173",  # Vite default dev server
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
]

# Add production origins from environment variable if set
production_origin = os.getenv("FRONTEND_URL")
if production_origin:
    origins.append(production_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sam_opportunities.router, prefix="/api")
app.include_router(govwin_opportunities.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(govwin_contracts.router, prefix="/api")
app.include_router(crm_integration.router, prefix="/api")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "SAM.gov & GovWin Opportunity Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload during development
    )
