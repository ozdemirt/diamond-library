"""
Database Management Module for Books Metadata Scanner.
Handles MySQL connection, SQLAlchemy ORM models, table migrations, and batch operations.
"""

import os
from typing import Dict, Any, List, Set, Tuple, Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    func,
    text,
    Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load environment variables
load_dotenv()

Base = declarative_base()


class Book(Base):
    """
    SQLAlchemy ORM Model representing the 'books' table.
    """
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)
    page_count = Column(Integer, nullable=True)
    file_type = Column(String(20), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    sha256_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_books_sha256", "sha256_hash", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Book model instance to dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author or "Bilinmiyor",
            "page_count": self.page_count if self.page_count is not None else "-",
            "file_type": self.file_type,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "sha256_hash": self.sha256_hash,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "-"
        }

    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title='{self.title}', author='{self.author}', file_type='{self.file_type}')>"


def get_db_config() -> Dict[str, Any]:
    """
    Read MySQL connection parameters from environment variables.
    """
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "books_db")
    }


def get_db_url(include_db: bool = True) -> str:
    """
    Construct the SQLAlchemy connection URL with PyMySQL driver.
    """
    cfg = get_db_config()
    encoded_user = quote_plus(cfg["user"])
    encoded_pass = quote_plus(cfg["password"])
    host = cfg["host"]
    port = cfg["port"]
    db_name = cfg["database"]

    if include_db:
        return f"mysql+pymysql://{encoded_user}:{encoded_pass}@{host}:{port}/{db_name}?charset=utf8mb4"
    else:
        return f"mysql+pymysql://{encoded_user}:{encoded_pass}@{host}:{port}/?charset=utf8mb4"


def create_database_if_not_exists() -> bool:
    """
    Connect to MySQL server without database name and create target database if missing.
    """
    cfg = get_db_config()
    db_name = cfg["database"]
    server_url = get_db_url(include_db=False)

    try:
        engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            conn.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
        engine.dispose()
        return True
    except Exception as e:
        # If server connection fails, let caller handle engine creation / error reporting
        return False


def get_engine(echo: bool = False):
    """
    Create and return a SQLAlchemy engine with connection pooling and health checks.
    """
    create_database_if_not_exists()
    db_url = get_db_url(include_db=True)
    engine = create_engine(
        db_url,
        echo=echo,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    return engine


def init_db(engine=None):
    """
    Initialize database schema by creating all defined tables.
    """
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine


def get_session(engine=None) -> Session:
    """
    Return a new SQLAlchemy Session instance.
    """
    if engine is None:
        engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_existing_hashes(session: Session) -> Set[str]:
    """
    Retrieve all existing SHA-256 hashes from the database for O(1) duplicate checks.
    """
    results = session.query(Book.sha256_hash).all()
    return {row[0] for row in results if row[0]}


def save_books_batch(session: Session, books_data: List[Dict[str, Any]]) -> int:
    """
    Insert a batch of book records into the database.
    Returns the number of records successfully saved.
    """
    if not books_data:
        return 0

    inserted_count = 0
    try:
        book_objects = []
        for item in books_data:
            # Clean string length constraints
            title = str(item.get("title", "İsimsiz Kitap"))[:255]
            author = str(item.get("author", "Bilinmiyor"))[:255] if item.get("author") else None
            file_type = str(item.get("file_type", "unknown"))[:20].lower()
            file_path = str(item.get("file_path", ""))[:500]
            page_count = item.get("page_count")
            file_size_bytes = int(item.get("file_size_bytes", 0))
            sha256_hash = str(item.get("sha256_hash", ""))[:64]

            book = Book(
                title=title,
                author=author,
                page_count=page_count,
                file_type=file_type,
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                sha256_hash=sha256_hash
            )
            book_objects.append(book)

        session.bulk_save_objects(book_objects)
        session.commit()
        inserted_count = len(book_objects)
    except Exception as e:
        session.rollback()
        # Fallback to individual inserts if batch hits a collision
        for item in books_data:
            try:
                title = str(item.get("title", "İsimsiz Kitap"))[:255]
                author = str(item.get("author", "Bilinmiyor"))[:255] if item.get("author") else None
                file_type = str(item.get("file_type", "unknown"))[:20].lower()
                file_path = str(item.get("file_path", ""))[:500]
                page_count = item.get("page_count")
                file_size_bytes = int(item.get("file_size_bytes", 0))
                sha256_hash = str(item.get("sha256_hash", ""))[:64]

                book = Book(
                    title=title,
                    author=author,
                    page_count=page_count,
                    file_type=file_type,
                    file_path=file_path,
                    file_size_bytes=file_size_bytes,
                    sha256_hash=sha256_hash
                )
                session.add(book)
                session.commit()
                inserted_count += 1
            except Exception:
                session.rollback()
                continue

    return inserted_count


def get_books_summary(session: Session, limit: int = 20) -> Tuple[int, List[Book]]:
    """
    Fetch total count of books in the database and first N records for display.
    """
    total_count = session.query(func.count(Book.id)).scalar() or 0
    sample_books = session.query(Book).order_by(Book.id.asc()).limit(limit).all()
    return total_count, sample_books


def get_all_books_from_db(session: Session) -> List[Book]:
    """
    Fetch all book records from MySQL 'books' table ordered by ID.
    """
    return session.query(Book).order_by(Book.id.asc()).all()

