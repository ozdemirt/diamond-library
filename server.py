"""
DiamondLibrary - High-Performance Multi-Threaded Web Server & REST API.
Powered by SQLite FTS5 Full-Text Search Engine with thread-safe connections.
Serves instant search, book catalog, reading viewer, and static web frontend.
"""

import os
import re
import json
import time
import threading
import urllib.parse
import sqlite3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, List, Any, Optional

PORT = int(os.environ.get("PORT", 8000))
DB_PATH = os.environ.get("DB_PATH", "search_index.db")
TXT_DIR = os.environ.get("TXT_DIR", "converted_texts")
STATIC_DIR = "static"

_local = threading.local()


def get_db() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    if not hasattr(_local, "con") or _local.con is None:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode = WAL;")
        con.execute("PRAGMA synchronous = NORMAL;")
        con.execute("PRAGMA cache_size = -32000;")
        _local.con = con
    return _local.con


def sanitize_search_query(q: str) -> str:
    """Sanitize and format query for SQLite FTS5 syntax."""
    if not q:
        return ""
    q = q.strip()
    if q.startswith('"') and q.endswith('"') and len(q) > 2:
        clean_inner = q[1:-1].replace('"', '""')
        return f'"{clean_inner}"'

    clean_words = re.findall(r'[\w\u00C0-\u017F]+', q)
    if not clean_words:
        return ""
    
    if len(clean_words) == 1:
        return f'"{clean_words[0]}"*'
    
    formatted = " AND ".join(f'"{w}"*' for w in clean_words)
    return formatted


class LibraryHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Powered-By", "DiamondLibrary FTS5 Engine")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json_response(self, data: Any, status: int = 200):
        """Send JSON response with UTF-8 encoding."""
        json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(json_bytes)))
        self.end_headers()
        self.wfile.write(json_bytes)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # 1. API: Stats & System Info
        if path == "/api/stats" or path == "/api":
            self.handle_stats()
            return

        # 2. API: Search
        elif path == "/api/search":
            self.handle_search(query_params)
            return

        # 3. API: Books Catalog
        elif path == "/api/books":
            self.handle_books_catalog(query_params)
            return

        # 4. API: Single Book Detail & Page Content
        elif path.startswith("/api/books/"):
            parts = path.strip("/").split("/")
            # /api/books/{id}
            if len(parts) == 3:
                try:
                    book_id = int(parts[2])
                    self.handle_book_detail(book_id)
                    return
                except ValueError:
                    pass
            # /api/books/{id}/page/{num}
            elif len(parts) == 5 and parts[3] == "page":
                try:
                    book_id = int(parts[2])
                    page_num = int(parts[4])
                    self.handle_book_page(book_id, page_num)
                    return
                except ValueError:
                    pass
            # /api/books/{id}/download
            elif len(parts) == 4 and parts[3] == "download":
                try:
                    book_id = int(parts[2])
                    self.handle_book_download(book_id)
                    return
                except ValueError:
                    pass

        # Serve Frontend Static Files
        if path == "/" or path == "":
            self.path = "/index.html"
        return super().do_GET()

    def handle_stats(self):
        """Return DiamondLibrary system-wide statistics."""
        con = get_db()
        cur = con.cursor()
        total_books = cur.execute("SELECT COUNT(*) FROM books;").fetchone()[0]
        total_pages = cur.execute("SELECT COUNT(*) FROM pages_fts;").fetchone()[0]
        words_row = cur.execute("SELECT SUM(total_words) FROM books;").fetchone()[0] or 0
        formats = cur.execute("SELECT file_type, COUNT(*) as cnt FROM books GROUP BY file_type;").fetchall()
        
        db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0

        self.send_json_response({
            "app_name": "DiamondLibrary API",
            "version": "1.0.0",
            "total_books": total_books,
            "total_pages": total_pages,
            "total_words": words_row,
            "db_size_mb": round(db_size_mb, 2),
            "formats": {r["file_type"]: r["cnt"] for r in formats}
        })

    def handle_search(self, params: Dict[str, List[str]]):
        """Execute ultra-fast SQLite FTS5 full-text search with BM25 ranking."""
        raw_q = params.get("q", [""])[0].strip()
        scope = params.get("scope", ["all"])[0]
        format_filter = params.get("format", [""])[0].upper()
        page = max(1, int(params.get("page", ["1"])[0]))
        limit = min(50, max(1, int(params.get("limit", ["15"])[0])))
        offset = (page - 1) * limit

        if not raw_q:
            self.send_json_response({"results": [], "total": 0, "query": "", "time_ms": 0})
            return

        fts_query = sanitize_search_query(raw_q)
        if not fts_query:
            self.send_json_response({"results": [], "total": 0, "query": raw_q, "time_ms": 0})
            return

        t0 = time.time()
        con = get_db()
        cur = con.cursor()

        try:
            # 1. Title/Author only search
            if scope == "title" or scope == "author":
                column_filter = "title" if scope == "title" else "author"
                where_clause = f"books_fts MATCH '{column_filter} : {fts_query}'"
                
                count_sql = f"SELECT COUNT(*) FROM books_fts WHERE {where_clause};"
                total_count = cur.execute(count_sql).fetchone()[0]

                sql = f"""
                SELECT b.id, b.title, b.author, b.file_type, b.total_pages, b.total_words, b.txt_filename
                FROM books_fts bf
                JOIN books b ON bf.book_id = b.id
                WHERE {where_clause}
                LIMIT ? OFFSET ?;
                """
                rows = cur.execute(sql, (limit, offset)).fetchall()
                results = []
                for r in rows:
                    results.append({
                        "book_id": r["id"],
                        "title": r["title"],
                        "author": r["author"] or "Bilinmiyor",
                        "file_type": r["file_type"],
                        "total_pages": r["total_pages"],
                        "total_words": r["total_words"],
                        "page_num": 1,
                        "snippet": f"Kitap: <strong>{r['title']}</strong> | Yazar: {r['author'] or '-'}"
                    })

            # 2. Full-Text Search inside pages (BM25 ranked with highlighted snippet)
            else:
                where_extra = ""
                extra_params = [fts_query]

                if format_filter and format_filter in ("PDF", "EPUB"):
                    where_extra = "AND b.file_type = ?"
                    extra_params.append(format_filter)

                # Total count
                count_sql = f"""
                SELECT COUNT(*) FROM pages_fts pf
                JOIN books b ON pf.book_id = b.id
                WHERE pages_fts MATCH ? {where_extra};
                """
                total_count = cur.execute(count_sql, extra_params).fetchone()[0]

                sql = f"""
                SELECT pf.book_id, pf.page_num, pf.title, pf.author, b.file_type, b.total_pages, b.total_words,
                       snippet(pages_fts, 4, '<mark>', '</mark>', '...', 25) as snippet_text
                FROM pages_fts pf
                JOIN books b ON pf.book_id = b.id
                WHERE pages_fts MATCH ? {where_extra}
                ORDER BY rank
                LIMIT ? OFFSET ?;
                """
                rows = cur.execute(sql, extra_params + [limit, offset]).fetchall()
                results = []
                for r in rows:
                    results.append({
                        "book_id": r["book_id"],
                        "title": r["title"],
                        "author": r["author"] or "Bilinmiyor",
                        "file_type": r["file_type"],
                        "total_pages": r["total_pages"],
                        "total_words": r["total_words"],
                        "page_num": r["page_num"],
                        "snippet": r["snippet_text"]
                    })

            elapsed_ms = round((time.time() - t0) * 1000, 2)
            self.send_json_response({
                "app": "DiamondLibrary",
                "results": results,
                "total": total_count,
                "page": page,
                "limit": limit,
                "query": raw_q,
                "time_ms": elapsed_ms
            })

        except Exception as e:
            self.send_json_response({"error": str(e), "results": [], "total": 0, "time_ms": 0}, status=500)

    def handle_books_catalog(self, params: Dict[str, List[str]]):
        """Return paginated list of all books for browsing."""
        page = max(1, int(params.get("page", ["1"])[0]))
        limit = min(100, max(1, int(params.get("limit", ["24"])[0])))
        offset = (page - 1) * limit
        format_filter = params.get("format", [""])[0].upper()
        search_q = params.get("q", [""])[0].strip()

        con = get_db()
        cur = con.cursor()
        where_clauses = []
        sql_params = []

        if format_filter in ("PDF", "EPUB"):
            where_clauses.append("file_type = ?")
            sql_params.append(format_filter)

        if search_q:
            where_clauses.append("(title LIKE ? OR author LIKE ?)")
            sql_params.extend([f"%{search_q}%", f"%{search_q}%"])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        total = cur.execute(f"SELECT COUNT(*) FROM books {where_sql};", sql_params).fetchone()[0]
        rows = cur.execute(f"""
        SELECT id, title, author, file_type, total_pages, total_words, txt_filename
        FROM books
        {where_sql}
        ORDER BY title ASC
        LIMIT ? OFFSET ?;
        """, sql_params + [limit, offset]).fetchall()

        books_list = [dict(r) for r in rows]
        self.send_json_response({
            "books": books_list,
            "total": total,
            "page": page,
            "limit": limit
        })

    def handle_book_detail(self, book_id: int):
        """Return metadata for a single book."""
        con = get_db()
        cur = con.cursor()
        row = cur.execute("SELECT * FROM books WHERE id = ?;", (book_id,)).fetchone()
        if not row:
            self.send_json_response({"error": "Kitap bulunamadı"}, status=404)
            return
        self.send_json_response(dict(row))

    def handle_book_page(self, book_id: int, page_num: int):
        """Return full text for a specific page of a book."""
        con = get_db()
        cur = con.cursor()
        book = cur.execute("SELECT * FROM books WHERE id = ?;", (book_id,)).fetchone()
        if not book:
            self.send_json_response({"error": "Kitap bulunamadı"}, status=404)
            return

        txt_filename = book["txt_filename"]
        txt_path = os.path.join(TXT_DIR, txt_filename)

        if not os.path.exists(txt_path):
            self.send_json_response({"error": "Metin dosyası bulunamadı"}, status=404)
            return

        try:
            with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                full_text = f.read()

            pattern = r'---\s*(?:Sayfa|Bölüm/Sayfa)\s*(\d+)\s*---'
            splits = re.split(pattern, full_text)

            page_content = ""
            total_found_pages = 1

            if len(splits) > 1:
                total_found_pages = (len(splits) - 1) // 2
                for i in range(1, len(splits), 2):
                    if int(splits[i]) == page_num:
                        page_content = splits[i + 1].strip()
                        break
            else:
                page_content = full_text.strip()

            self.send_json_response({
                "book_id": book_id,
                "title": book["title"],
                "author": book["author"],
                "file_type": book["file_type"],
                "page_num": page_num,
                "total_pages": book["total_pages"] or total_found_pages,
                "content": page_content or "[Bu sayfa için metin içeriği bulunamadı.]"
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_book_download(self, book_id: int):
        """Allow user to download the UTF-8 TXT file."""
        con = get_db()
        cur = con.cursor()
        book = cur.execute("SELECT * FROM books WHERE id = ?;", (book_id,)).fetchone()
        if not book:
            self.send_error(404, "Kitap bulunamadı")
            return

        txt_path = os.path.join(TXT_DIR, book["txt_filename"])
        if not os.path.exists(txt_path):
            self.send_error(404, "Dosya bulunamadı")
            return

        with open(txt_path, "rb") as f:
            file_bytes = f.read()

        filename_encoded = urllib.parse.quote(book["txt_filename"])
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{filename_encoded}")
        self.send_header("Content-Length", str(len(file_bytes)))
        self.end_headers()
        self.wfile.write(file_bytes)


def run_server(port: int = PORT):
    os.makedirs(STATIC_DIR, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", port), LibraryHTTPHandler)
    print("=" * 80)
    print(f" 💎  DIAMONDLIBRARY - TAM METİN ARAMA SUNUCUSU BAŞLATILDI  💎")
    print("=" * 80)
    print(f"  • Yerel Erişim Adresi : http://localhost:{port}")
    print(f"  • Arama Motoru        : SQLite FTS5 (1.913 Kitap / 429.308 Sayfa / ~120M Kelime)")
    print(f"  • Çalışma Modu        : Multi-Threaded HTTP REST API + Frontend")
    print("=" * 80 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Sunucu durduruldu.")
        server.server_close()


if __name__ == "__main__":
    run_server()
