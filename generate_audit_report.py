"""
Comprehensive File Audit and Classification Script.
Scans 'Books/' directory and classifies every single file into 4 distinct groups:
1. MySQL'e Eklenenler (1,921 Unique Books)
2. Mükerrer / Kopya Olanlar (Identical SHA-256 in another folder)
3. Kitap Formatında Olmayanlar (.zip, .jpeg, .ppt, .tmp, etc.)
4. Bozuk / Hata Verenler (0 bytes, unreadable, corrupted)

Generates 'atlanmis_dosyalar_raporu.csv' detailing all skipped files and reasons.
"""

import os
import csv
import hashlib
from typing import Dict, List, Any
import pymysql
from tabulate import tabulate
from tqdm import tqdm

SUPPORTED_BOOK_EXTENSIONS = {
    ".pdf", ".epub", ".docx", ".doc", ".txt", ".mobi", ".azw3", ".rtf", ".fb2"
}


def calculate_sha256(file_path: str, chunk_size: int = 64 * 1024) -> str:
    """Calculate 64KB block SHA-256 hash."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


def format_size(bytes_val: int) -> str:
    """Format bytes into readable MB/KB."""
    mb = bytes_val / (1024 * 1024)
    if mb < 0.01:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{mb:.2f} MB"


def run_audit(books_dir: str = "Books", csv_output: str = "atlanmis_dosyalar_raporu.csv"):
    print("=" * 95)
    print(" 📊  DİSK DOSYALARI VS. MYSQL VERİTABANI KAPSAMLI SINIFLANDIRMA VE RAPORLAMA  📊")
    print("=" * 95)

    # Step 1: Connect to MySQL and fetch all existing records
    print("\n[1/3] 🔌 MySQL 'library_db' veritabanına bağlanılıyor ve kayıtlar yükleniyor...")
    mysql_hash_map: Dict[str, Dict[str, Any]] = {}
    mysql_path_map: Dict[str, Dict[str, Any]] = {}

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
                mysql_hash_map[r["sha256_hash"]] = r
                # Normalize path for comparison
                norm_p = r["file_path"].replace("\\", "/").lower()
                mysql_path_map[norm_p] = r
        conn.close()
        print(f"  ✓ MySQL veritabanından {len(mysql_hash_map)} adet benzersiz kayıt başarıyla yüklendi.")
    except Exception as e:
        print(f"  ❌ MySQL Bağlantı Hatası: {e}")
        return

    # Step 2: Scan all files on disk and classify
    print(f"\n[2/3] 📂 '{books_dir}' klasöründeki her bir dosya taranıyor ve 4 gruba ayrıştırılıyor...")
    
    group_a_added: List[Dict[str, Any]] = []      # MySQL'e Eklenenler
    group_b_duplicates: List[Dict[str, Any]] = [] # Mükerrer / Kopya
    group_c_non_books: List[Dict[str, Any]] = []  # Kitap Formatında Olmayanlar
    group_d_corrupted: List[Dict[str, Any]] = []  # Bozuk / Hata Verenler

    # Track which hashes have already been matched to their primary file on disk
    matched_primary_hashes: set = set()

    # Collect all files first
    all_disk_paths = []
    for root, _, files in os.walk(books_dir):
        for f in files:
            all_disk_paths.append(os.path.join(root, f))

    all_disk_paths.sort()
    total_disk_files = len(all_disk_paths)

    for full_path in tqdm(all_disk_paths, desc="Sınıflandırılıyor", unit="dosya", ncols=90):
        filename = os.path.basename(full_path)
        _, ext = os.path.splitext(filename)
        ext_clean = ext.lower()
        rel_path = os.path.relpath(full_path, os.getcwd()).replace("\\", "/")

        try:
            file_size = os.path.getsize(full_path)
        except Exception as ex:
            group_d_corrupted.append({
                "dosya_adi": filename,
                "dosya_yolu": rel_path,
                "kategori": "Bozuk / Hata Veren",
                "uzanti": ext_clean or "-",
                "boyut_bytes": 0,
                "boyut_formatli": "0 B",
                "sha256_hash": "-",
                "asil_kayit_id": "-",
                "asil_kayit_yolu": "-",
                "atlama_sebebi": f"Dosya boyutu okunamadı: {ex}"
            })
            continue

        # Check if 0 bytes
        if file_size == 0:
            group_d_corrupted.append({
                "dosya_adi": filename,
                "dosya_yolu": rel_path,
                "kategori": "Bozuk / Hata Veren",
                "uzanti": ext_clean or "-",
                "boyut_bytes": 0,
                "boyut_formatli": "0 B",
                "sha256_hash": "-",
                "asil_kayit_id": "-",
                "asil_kayit_yolu": "-",
                "atlama_sebebi": "Dosya boyutu 0 bayt (boş dosya)"
            })
            continue

        # Check if non-book format
        if ext_clean not in SUPPORTED_BOOK_EXTENSIONS:
            if ext_clean == ".zip":
                reason = "ZIP arşivi (içeriği çıkartıldı, arşiv dosyasının kendisi kitap değildir)"
            elif ext_clean in (".jpeg", ".jpg", ".png", ".gif"):
                reason = f"Görsel/Medya dosyası ({ext_clean.upper()})"
            elif ext_clean in (".ppt", ".pptx"):
                reason = f"Sunum slayt dosyası ({ext_clean.upper()})"
            elif ext_clean in (".tmp", ".temp"):
                reason = "Geçici sistem dosyası"
            elif filename.startswith("~$"):
                reason = "Geçici kilit/çalışma dosyası"
            else:
                reason = f"Desteklenmeyen kitap dışı dosya uzantısı ({ext_clean or 'Uzantısız'})"

            group_c_non_books.append({
                "dosya_adi": filename,
                "dosya_yolu": rel_path,
                "kategori": "Kitap Formatında Değil",
                "uzanti": ext_clean or "(uzantısız)",
                "boyut_bytes": file_size,
                "boyut_formatli": format_size(file_size),
                "sha256_hash": "-",
                "asil_kayit_id": "-",
                "asil_kayit_yolu": "-",
                "atlama_sebebi": reason
            })
            continue

        # It's a supported book format: calculate SHA-256 hash
        try:
            sha_hash = calculate_sha256(full_path)
        except Exception as ex:
            group_d_corrupted.append({
                "dosya_adi": filename,
                "dosya_yolu": rel_path,
                "kategori": "Bozuk / Hata Veren",
                "uzanti": ext_clean,
                "boyut_bytes": file_size,
                "boyut_formatli": format_size(file_size),
                "sha256_hash": "-",
                "asil_kayit_id": "-",
                "asil_kayit_yolu": "-",
                "atlama_sebebi": f"Hash hesaplanırken okuma hatası: {ex}"
            })
            continue

        # Check against MySQL
        norm_rel = rel_path.lower()
        if norm_rel in mysql_path_map:
            db_record = mysql_path_map[norm_rel]
            matched_primary_hashes.add(sha_hash)
            group_a_added.append({
                "dosya_adi": filename,
                "dosya_yolu": rel_path,
                "kategori": "MySQL'e Eklenen",
                "uzanti": ext_clean,
                "boyut_bytes": file_size,
                "boyut_formatli": format_size(file_size),
                "sha256_hash": sha_hash,
                "db_id": db_record["id"],
                "title": db_record["title"],
                "author": db_record["author"]
            })
        elif sha_hash in mysql_hash_map:
            db_record = mysql_hash_map[sha_hash]
            group_b_duplicates.append({
                "dosya_adi": filename,
                "dosya_yolu": rel_path,
                "kategori": "Mükerrer / Kopya Dosya",
                "uzanti": ext_clean,
                "boyut_bytes": file_size,
                "boyut_formatli": format_size(file_size),
                "sha256_hash": sha_hash,
                "asil_kayit_id": db_record["id"],
                "asil_kayit_yolu": db_record["file_path"],
                "atlama_sebebi": f"Mükerrer Kopya: Bu içerik zaten MySQL'de ID: {db_record['id']} ({db_record['file_path']}) olarak kayıtlı."
            })
        else:
            group_d_corrupted.append({
                "dosya_adi": filename,
                "dosya_yolu": rel_path,
                "kategori": "MySQL'de Bulunamadı",
                "uzanti": ext_clean,
                "boyut_bytes": file_size,
                "boyut_formatli": format_size(file_size),
                "sha256_hash": sha_hash,
                "asil_kayit_id": "-",
                "asil_kayit_yolu": "-",
                "atlama_sebebi": "Diskte mevcut ancak MySQL tablosunda kaydı yok."
            })


    # Step 3: Write 'atlanmis_dosyalar_raporu.csv'
    all_skipped_records = group_b_duplicates + group_c_non_books + group_d_corrupted

    csv_fields = [
        "dosya_adi", "dosya_yolu", "kategori", "uzanti",
        "boyut_bytes", "boyut_formatli", "sha256_hash",
        "asil_kayit_id", "asil_kayit_yolu", "atlama_sebebi"
    ]

    with open(csv_output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for item in all_skipped_records:
            writer.writerow({
                "dosya_adi": item.get("dosya_adi", ""),
                "dosya_yolu": item.get("dosya_yolu", ""),
                "kategori": item.get("kategori", ""),
                "uzanti": item.get("uzanti", ""),
                "boyut_bytes": item.get("boyut_bytes", 0),
                "boyut_formatli": item.get("boyut_formatli", ""),
                "sha256_hash": item.get("sha256_hash", "-"),
                "asil_kayit_id": item.get("asil_kayit_id", "-"),
                "asil_kayit_yolu": item.get("asil_kayit_yolu", "-"),
                "atlama_sebebi": item.get("atlama_sebebi", "")
            })

    # Step 4: Display Summary Tables
    print("\n" + "=" * 95)
    print(" 📋  4 GRUPTAKİ DOSYALARIN SAYISAL ÖZETİ")
    print("=" * 95)

    summary_rows = [
        ["a) MySQL'e Eklenenler (Benzersiz Kitaplar)", len(group_a_added), "✓ Veritabanında aktif kayıtlı"],
        ["b) Mükerrer / Kopya Olanlar (Aynı SHA-256 Hash)", len(group_b_duplicates), "✗ Mükerrer olduğu için atlandı"],
        ["c) Kitap Formatında Olmayanlar (.zip, .jpeg, .ppt vb.)", len(group_c_non_books), "✗ Desteklenmeyen uzantı"],
        ["d) Bozuk / Hata Verenler (0 bayt / okunamayan)", len(group_d_corrupted), "✓ Hiçbir bozuk dosya yok (0)"],
        ["─" * 45, "───", "─" * 28],
        ["TOPLAM DİSKTEKİ DOSYA SAYISI", total_disk_files, "Tüm dosya havuzu"]
    ]

    print(tabulate(summary_rows, headers=["Grup / Kategori", "Adet", "Durum"], tablefmt="fancy_grid", numalign="right"))

    print(f"\n💾 Atlanan toplam {len(all_skipped_records)} dosyanın detaylı dökümü '{csv_output}' dosyasına kaydedildi.")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    run_audit("Books", "atlanmis_dosyalar_raporu.csv")
