from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import re, os


uri = os.getenv("DATABASE_URL")


def start() -> scoped_session:
    if uri.startswith("postgres"):
        DB_URI = uri.replace("postgres", "postgresql", 1)
        engine = create_engine(DB_URI, client_encoding="utf8")
        BASE.metadata.bind = engine
        BASE.metadata.create_all(engine)
        return scoped_session(sessionmaker(bind=engine, autoflush=False))


BASE = declarative_base()
SESSION = start()
