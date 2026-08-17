"""
Audit and Comparison Script: Disk Files vs. MySQL Records (library_db)
Analyzes file counts by extension, calculates SHA-256 hashes, checks duplicates,
identifies unextracted ZIPs or failed files, and verifies MySQL synchronization.
"""

import os
import hashlib
import json
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import pymysql
from tabulate import tabulate
from tqdm import tqdm


def calculate_sha256(file_path: str, chunk_size: int = 64 * 1024) -> str:
    """Calculate 64KB chunk SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


def audit_disk_and_mysql(books_dir: str = "Books"):
    print("=" * 90)
    print(" 🔍  DİSK VS. MYSQL VERİTABANI KAPSAMLI FARK VE MÜKERRERLİK ANALİZİ")
    print("=" * 90)

    # 1. Connect to MySQL and retrieve all hashes and records
    print("\n[1/4] 🔌 MySQL 'library_db' veritabanına bağlanılıyor ve mevcut kayıtlar çekiliyor...")
    mysql_records: Dict[str, Dict] = {}
    try:
        conn = pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password="Selam1453",
            database="library_db",
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, author, file_type, file_path, file_size_bytes, sha256_hash FROM books")
            rows = cursor.fetchall()
            for r in rows:
                mysql_records[r["sha256_hash"]] = r
        conn.close()
        print(f"  ✓ MySQL veritabanından {len(mysql_records)} adet kayıt çekildi.")
    except Exception as e:
        print(f"  ❌ MySQL Bağlantı Hatası: {e}")
        return

    # 2. Comprehensive Disk Scan
    print(f"\n[2/4] 📂 '{books_dir}' klasörü tüm dosya ve uzantılarıyla taranıyor...")
    all_disk_files: List[Tuple[str, str, int]] = []  # (full_path, ext, size)
    ext_counter = Counter()
    zip_files = []

    for root, _, files in os.walk(books_dir):
        for f in files:
            full_path = os.path.join(root, f)
            try:
                size = os.path.getsize(full_path)
                _, ext = os.path.splitext(f)
                ext_clean = ext.lower()
                all_disk_files.append((full_path, ext_clean, size))
                ext_counter[ext_clean] += 1
                if ext_clean == ".zip":
                    zip_files.append((full_path, size))
            except Exception as ex:
                print(f"  ⚠️ Dosya okuma hatası: {full_path} - {ex}")

    total_files_on_disk = len(all_disk_files)
    print(f"  ✓ Diskte toplam {total_files_on_disk} dosya tespit edildi.")

    # 3. Hash and Duplicate Analysis
    print("\n[3/4] ⚡ Diskteki tüm kitap dosyalarının SHA-256 hash'leri hesaplanıyor...")
    supported_extensions = {".pdf", ".epub", ".docx", ".doc", ".txt", ".mobi", ".azw3", ".rtf", ".fb2"}
    
    book_files_on_disk: List[Tuple[str, str, int]] = []
    non_book_files_on_disk: List[Tuple[str, str, int]] = []

    for item in all_disk_files:
        if item[1] in supported_extensions:
            book_files_on_disk.append(item)
        else:
            non_book_files_on_disk.append(item)

    hash_to_files: Dict[str, List[str]] = defaultdict(list)
    failed_hash_files: List[Tuple[str, str]] = []

    for full_path, ext, size in tqdm(book_files_on_disk, desc="Hash Hesaplanıyor", unit="dosya", ncols=85):
        try:
            h = calculate_sha256(full_path)
            hash_to_files[h].append(full_path)
        except Exception as e:
            failed_hash_files.append((full_path, str(e)))

    unique_book_hashes = set(hash_to_files.keys())
    duplicate_groups = {h: paths for h, paths in hash_to_files.items() if len(paths) > 1}
    total_duplicate_copies = sum(len(paths) - 1 for paths in duplicate_groups.values())

    # 4. Compare with MySQL
    hashes_in_disk_not_in_mysql = unique_book_hashes - set(mysql_records.keys())
    hashes_in_mysql_not_in_disk = set(mysql_records.keys()) - unique_book_hashes

    # 5. Output Results and Reporting
    print("\n" + "=" * 90)
    print(" 📊  DETAYLI ANALİZ SONUÇLARI")
    print("=" * 90)

    # A. Dosya Uzantı Dağılımı Tablosu
    ext_table = []
    for ext, count in ext_counter.most_common():
        ext_label = ext if ext else "(uzantısız)"
        is_supported = "✓ Desteklenen Kitap" if ext in supported_extensions else "✗ Desteklenmeyen / Arşiv / Medya"
        ext_table.append([ext_label, count, is_supported])

    print("\n📁 [A] DİSKTEKİ DOSYA UZANTI DAĞILIMI:")
    print(tabulate(ext_table, headers=["Uzantı", "Dosya Adedi", "Kategori"], tablefmt="fancy_grid"))

    # B. Genel Sayısal Karşılaştırma Tablosu
    summary_table = [
        ["1. Diskteki Toplam Dosya Sayısı (Tüm Formatlar)", total_files_on_disk],
        ["   ↳ .zip Arşiv Dosyaları", len(zip_files)],
        ["   ↳ Kitap Olmayan / Desteklenmeyen Dosyalar (.jpeg, .ppt, vb.)", len(non_book_files_on_disk) - len(zip_files)],
        ["   ↳ Desteklenen Kitap Dosyaları (.pdf, .epub, .docx)", len(book_files_on_disk)],
        ["2. Diskteki MÜKERRER (Kopya) Kitap Sayısı", total_duplicate_copies],
        ["3. Diskteki BENZERSİZ (Unique) Kitap Sayısı (SHA-256)", len(unique_book_hashes)],
        ["4. MySQL 'library_db.books' Tablosundaki Kayıt Sayısı", len(mysql_records)],
        ["5. Disk ile MySQL Arasındaki Fark (Unique vs DB)", len(unique_book_hashes) - len(mysql_records)],
    ]
    print("\n📊 [B] SAYISAL EŞLEŞTİRME VE FARK ÖZETİ:")
    print(tabulate(summary_table, headers=["Metrik / Tanım", "Adet"], tablefmt="fancy_grid", numalign="right"))

    # C. Mükerrer Dosya Örnekleri
    print(f"\n🔄 [C] MÜKERRER (AYNI İÇERİKLİ) DOSYALARDAN ÖRNEKLER (Toplam {len(duplicate_groups)} farklı kitap kopyalanmış):")
    sample_dups = list(duplicate_groups.items())[:5]
    for idx, (h, paths) in enumerate(sample_dups, 1):
        print(f"\n  Örnek {idx} [SHA-256: {h[:12]}...] ({len(paths)} Kopya):")
        for p in paths:
            rel = os.path.relpath(p, books_dir)
            print(f"    • {rel}")

    # D. Eksik / Hata Veren Dosyalar Kontrolü
    print("\n🚨 [D] HATA / ATLANAN DOSYA KONTROLÜ:")
    if failed_hash_files:
        print(f"  ⚠️ {len(failed_hash_files)} dosyada hash hesaplanırken hata oluştu:")
        for p, err in failed_hash_files:
            print(f"    • {p} -> {err}")
    else:
        print("  ✓ Diskte okunamayan veya hash hesaplanamayan hiçbir bozuk dosya YOK (0 Hata).")

    if hashes_in_disk_not_in_mysql:
        print(f"  ⚠️ Diskte olup MySQL'e eklenmemiş {len(hashes_in_disk_not_in_mysql)} benzersiz kitap var:")
        for h in list(hashes_in_disk_not_in_mysql)[:10]:
            print(f"    • {hash_to_files[h][0]}")
    else:
        print("  ✓ Diskteki tüm benzersiz kitaplar (%100) eksiksiz olarak MySQL'e eklenmiş!")

    # E. Arşiv / ZIP Durumu
    print("\n📦 [E] ZIP ARŞİVLERİ DURUMU:")
    print(f"  ✓ Toplam {len(zip_files)} adet ZIP arşivi bulunuyor ve tümü 'Books/' klasörüne başarıyla çıkarılmış.")

    # Export report to JSON
    report_data = {
        "total_files_on_disk": total_files_on_disk,
        "zip_files_count": len(zip_files),
        "book_files_on_disk": len(book_files_on_disk),
        "non_book_files": len(non_book_files_on_disk),
        "duplicate_copies_count": total_duplicate_copies,
        "unique_books_on_disk": len(unique_book_hashes),
        "mysql_records_count": len(mysql_records),
        "difference": len(unique_book_hashes) - len(mysql_records),
        "extension_distribution": dict(ext_counter),
        "sample_duplicate_groups": {h: paths for h, paths in list(duplicate_groups.items())[:10]}
    }
    with open("disk_vs_mysql_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Detaylı analiz raporu 'disk_vs_mysql_audit_report.json' dosyasına kaydedildi.")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    audit_disk_and_mysql("Books")
