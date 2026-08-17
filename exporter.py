"""
Data Exporter Module for Books Metadata Scanner.
Exports book records fetched directly from MySQL database to JSON and CSV formats.
"""

import csv
import json
import os
from typing import List, Union, Dict, Any
from database import Book


def export_to_json(books: List[Union[Book, Dict[str, Any]]], output_path: str = "books_from_db.json") -> str:
    """
    Export database records to a formatted JSON file with UTF-8 encoding.
    """
    data = []
    for b in books:
        if isinstance(b, Book):
            data.append(b.to_dict())
        elif isinstance(b, dict):
            data.append(b)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return os.path.abspath(output_path)


def export_to_csv(books: List[Union[Book, Dict[str, Any]]], output_path: str = "books_from_db.csv") -> str:
    """
    Export database records to a CSV file with UTF-8 encoding.
    """
    fieldnames = [
        "id", "title", "author", "page_count", "file_type",
        "file_path", "file_size_bytes", "sha256_hash", "created_at"
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for b in books:
            if isinstance(b, Book):
                row = b.to_dict()
            elif isinstance(b, dict):
                row = b
            else:
                continue

            writer.writerow({
                "id": row.get("id"),
                "title": row.get("title", ""),
                "author": row.get("author", ""),
                "page_count": row.get("page_count", ""),
                "file_type": row.get("file_type", ""),
                "file_path": row.get("file_path", ""),
                "file_size_bytes": row.get("file_size_bytes", 0),
                "sha256_hash": row.get("sha256_hash", ""),
                "created_at": row.get("created_at", "")
            })

    return os.path.abspath(output_path)
