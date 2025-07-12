from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from config import DATABASE_URI
from models import Base

# Create a database engine
# The connect_args are specific to SQLite to allow shared cache and prevent issues with threads
# For other databases, these connect_args might not be necessary or different.
engine_args = {}
if DATABASE_URI.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URI, **engine_args)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a scoped session factory to ensure thread safety for sessions
# This is particularly useful in web applications or bots where multiple requests are handled concurrently.
db_session = scoped_session(SessionLocal)

def init_db():
    """
    Initializes the database by creating all tables defined in models.py.
    This function should be called once when the application starts.
    """
    # Import all modules here that might define models so that
    # they will be registered properly on the metadata. Otherwise
    # you will have to import them first before calling init_db().
    # In this case, models.Base should already have them.
    Base.metadata.create_all(bind=engine)
    print("Database initialized: Tables created if they didn't exist.")

def get_db():
    """
    Provides a database session for use in other parts of the application.
    It's designed to be used as a context manager or a dependency.
    Example usage:
        db = get_db()
        try:
            # ... do something with db ...
            db.commit()
        except:
            db.rollback()
            raise
        finally:
            db.close() # Important to close the session to return it to the pool

    For applications using frameworks like FastAPI, dependency injection handles this.
    For this bot, we'll need to manage it carefully or use db_session directly.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Optional: A context manager for sessions if not using scoped_session directly
from contextlib import contextmanager

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

# At the application shutdown, it's good practice to remove the scoped session.
def shutdown_session():
    db_session.remove()

if __name__ == "__main__":
    # This is for demonstration or direct script execution to initialize the DB.
    # In a real application, init_db() would be called from the main entry point.
    print(f"Initializing database with URI: {DATABASE_URI}")
    init_db()

    # Example of using the session
    with session_scope() as session:
        # You can perform some initial data setup or checks here
        print("Database session acquired and released.")
        pass

    print("If you saw no errors, database.py is likely configured correctly.")
