#!/bin/bash

# Install ODBC driver for SQL Server if not already installed
if [ ! -f "/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.so" ]; then
    echo "ODBC driver not found, trying to use available driver..."
fi

# Start the FastAPI application
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app.main:app --bind=0.0.0.0:8000 --timeout 120
