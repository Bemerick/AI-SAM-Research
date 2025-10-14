"""
Main application module for the SAM.gov API client.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router as opportunities_router
from app.config import SAM_API_KEY

app = FastAPI(
    title="SAM.gov API Client",
    description="A Python application for retrieving opportunities from SAM.gov using their public API.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include the opportunities router
app.include_router(opportunities_router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint that returns basic API information."""
    return {
        "name": "SAM.gov API Client",
        "version": "1.0.0",
        "description": "A Python application for retrieving opportunities from SAM.gov using their public API.",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    if not SAM_API_KEY:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "SAM.gov API key is not configured."},
        )
    
    return {"status": "healthy", "api_key_configured": bool(SAM_API_KEY)}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for the application."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected error occurred: {str(exc)}"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
