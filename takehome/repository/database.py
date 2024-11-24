"""
Returns a database singleton
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

__SESSION = None

@contextmanager
def get_db():
    """
    Make sure this is singleton
    :return:
    """
    global __SESSION
    if __SESSION is None:
        __SESSION = SessionLocal(
            bind=engine.execution_options(isolation_level="SERIALIZABLE")
        )
    try:
        yield __SESSION
    finally:
        __SESSION.close()
