"""
Database configuration and session management.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv
import struct
from datetime import datetime, timedelta

load_dotenv()

# Database URL from environment variable
# Format: postgresql://user:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/sam_govwin"
)


def decode_mssql_datetime2(value):
    """
    Decode MS SQL Server DATETIME2 binary format to Python datetime.
    DATETIME2 is stored as 8 bytes: time (5 bytes) + date (3 bytes)
    """
    if isinstance(value, bytes) and len(value) == 8:
        try:
            # Extract time part (first 5 bytes) and date part (last 3 bytes)
            time_bytes = value[:5] + b'\x00\x00\x00'  # Pad to 8 bytes
            date_bytes = value[5:] + b'\x00\x00\x00\x00\x00'  # Pad to 8 bytes

            # Decode time as ticks (100-nanosecond intervals)
            time_ticks = struct.unpack('<Q', time_bytes)[0] & 0xFFFFFFFFFF

            # Decode date as days since 0001-01-01
            date_days = struct.unpack('<Q', date_bytes)[0] & 0xFFFFFF

            # Convert to Python datetime
            base_date = datetime(1, 1, 1)
            result_date = base_date + timedelta(days=date_days)
            result_time = timedelta(microseconds=time_ticks / 10)

            return result_date + result_time
        except Exception:
            # If decoding fails, return None
            return None
    return value


# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,         # Connection pool size
    max_overflow=10,     # Allow up to 10 connections beyond pool_size
    echo=False,          # Set to True for SQL query logging during development
)

# Add event listener for MS SQL datetime2 handling
if "mssql" in DATABASE_URL and "pymssql" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Configure connection to handle datetime properly."""
        # Register output converter for datetime2
        if hasattr(dbapi_conn, '_conn'):
            # pymssql specific handling
            pass  # pymssql doesn't support custom type converters easily

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Use with FastAPI Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    """
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def drop_db():
    """
    Drop all database tables.
    WARNING: This will delete all data!
    """
    import app.models  # noqa: F401
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped!")
