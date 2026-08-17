"""
High-Speed Search Indexer for Book Library.
Scans all 1,821+ converted TXT books in 'converted_texts/',
splits them by page, and indexes everything into a high-performance
SQLite FTS5 full-text search database 'search_index.db'.
"""

import os
import re
import csv
import json
import time
import sqlite3
from typing import Dict, List, Tuple, Any, Optional
from tqdm import tqdm


def init_database(db_path: str = "search_index.db") -> sqlite3.Connection:
    """Initialize SQLite FTS5 database schema."""
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Optimization Pragmas
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    cur.execute("PRAGMA temp_store = MEMORY;")

    # Books Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT,
        file_type TEXT,
        total_pages INTEGER DEFAULT 0,
        total_words INTEGER DEFAULT 0,
        txt_filename TEXT UNIQUE NOT NULL,
        original_rel_path TEXT
    );
    """)

    # Full-Text Search Virtual Table (FTS5 with unicode61 & diacritic removal)
    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
        book_id UNINDEXED,
        page_num UNINDEXED,
        title,
        author,
        content,
        tokenize = 'unicode61 remove_diacritics 2'
    );
    """)

    # Book Title / Author FTS Table for instant title autocompletion
    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
        book_id UNINDEXED,
        title,
        author,
        tokenize = 'unicode61 remove_diacritics 2'
    );
    """)

    con.commit()
    return con


def parse_pages_from_txt(txt_path: str) -> List[Tuple[int, str]]:
    """
    Parse TXT file into a list of (page_num, page_content).
    Detects '--- Sayfa N ---' or '--- Bölüm/Sayfa N ---' markers.
    """
    try:
        with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
            full_text = f.read()
    except Exception:
        return []

    if not full_text.strip():
        return []

    # Regex to split on page headers
    pattern = r'---\s*(?:Sayfa|Bölüm/Sayfa)\s*(\d+)\s*---'
    splits = re.split(pattern, full_text)

    pages = []
    if len(splits) <= 1:
        # No page markers found; treat whole text as Page 1
        clean_c = full_text.strip()
        if clean_c:
            pages.append((1, clean_c))
        return pages

    # The first element before the first marker (often empty or intro)
    intro = splits[0].strip()
    if intro:
        pages.append((1, intro))

    # Iterate over (page_number_str, content_str)
    for i in range(1, len(splits), 2):
        try:
            p_num = int(splits[i])
        except ValueError:
            p_num = len(pages) + 1
        p_content = splits[i + 1].strip() if i + 1 < len(splits) else ""
        if p_content:
            pages.append((p_num, p_content))

    return pages


def build_search_index(
    txt_dir: str = "converted_texts",
    summary_json_path: str = "converted_texts_summary.json",
    db_path: str = "search_index.db"
):
    print("=" * 85)
    print(" 🚀  TAM METİN ARAMA İNDEKSİ OLUŞTURULUYOR (SQLite FTS5)  🚀")
    print("=" * 85)

    if not os.path.exists(txt_dir):
        print(f"❌ HATA: '{txt_dir}' klasörü bulunamadı!")
        return

    # Load metadata if available
    metadata_map: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(summary_json_path):
        try:
            with open(summary_json_path, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
                for item in summary_data.get("detaylar", []):
                    txt_name = item.get("txt_dosyasi")
                    if txt_name:
                        metadata_map[txt_name] = item
        except Exception:
            pass

    # Discover all TXT files
    txt_files = [f for f in os.listdir(txt_dir) if f.lower().endswith(".txt")]
    txt_files.sort()
    total_txt = len(txt_files)
    print(f"  ✓ {total_txt} adet TXT kitabı indeksleme için tespit edildi.")
    print(f"  📁 Hedef İndeks Veritabanı: {os.path.abspath(db_path)}")
    print("-" * 85)

    con = init_database(db_path)
    cur = con.cursor()

    start_time = time.time()
    total_indexed_pages = 0
    total_indexed_words = 0
    indexed_books_count = 0

    cur.execute("BEGIN TRANSACTION;")

    with tqdm(total=total_txt, desc="İndeksleniyor", unit="kitap", ncols=85) as pbar:
        for txt_filename in txt_files:
            txt_path = os.path.join(txt_dir, txt_filename)
            meta = metadata_map.get(txt_filename, {})

            # Clean Title from filename
            base_name, _ = os.path.splitext(txt_filename)
            clean_title = base_name.replace("-", " ").replace("_", " ")
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            
            author = meta.get("yazar", "")
            file_type = meta.get("format", "TXT")
            original_path = meta.get("kaynak_yol", "")

            # Attempt to extract author from title if formatted like "Author - Title"
            if not author and " - " in clean_title:
                parts = clean_title.split(" - ", 1)
                author = parts[0].strip()
                clean_title = parts[1].strip()

            pages = parse_pages_from_txt(txt_path)
            book_words = sum(len(p[1].split()) for p in pages)
            book_pages_count = len(pages)

            # Insert into books table
            cur.execute("""
            INSERT INTO books (title, author, file_type, total_pages, total_words, txt_filename, original_rel_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (clean_title, author, file_type, book_pages_count, book_words, txt_filename, original_path))

            book_id = cur.lastrowid

            # Insert into books_fts
            cur.execute("""
            INSERT INTO books_fts (book_id, title, author)
            VALUES (?, ?, ?)
            """, (book_id, clean_title, author))

            # Insert pages into pages_fts
            for page_num, page_content in pages:
                cur.execute("""
                INSERT INTO pages_fts (book_id, page_num, title, author, content)
                VALUES (?, ?, ?, ?, ?)
                """, (book_id, page_num, clean_title, author, page_content))
                total_indexed_pages += 1

            total_indexed_words += book_words
            indexed_books_count += 1
            pbar.update(1)

    con.commit()
    con.close()

    elapsed = round(time.time() - start_time, 2)
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)

    print("\n" + "=" * 85)
    print(" ✨ İNDEKSLENEN VERİTABANI BAŞARIYLA OLUŞTURULDU ✨")
    print("=" * 85)
    print(f"  • İndekslenen Kitap Sayısı : {indexed_books_count:,}")
    print(f"  • İndekslenen Sayfa Sayısı : {total_indexed_pages:,}")
    print(f"  • İndekslenen Kelime Sayısı: {total_indexed_words:,}")
    print(f"  • Veritabanı Dosya Boyutu  : {db_size_mb:.2f} MB")
    print(f"  • Toplam İndeksleme Süresi : {elapsed} saniye")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    build_search_index()
