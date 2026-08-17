"""
DiamondLibrary - Books Metadata Scanner, MySQL Synchronizer and Reporter.
Scans the 'Books' directory, computes 64KB SHA-256 hashes, extracts metadata,
performs batch database insertions, executes SELECT query on MySQL to display tabular report,
and exports database records to JSON and CSV.
"""

import os
import sys
import time
from typing import List, Set
from dotenv import load_dotenv
from tqdm import tqdm
from tabulate import tabulate

from database import (
    get_db_config,
    get_engine,
    init_db,
    get_session,
    get_existing_hashes,
    save_books_batch,
    get_books_summary,
    get_all_books_from_db,
    Book
)
from parsers import extract_metadata
from exporter import export_to_json, export_to_csv

# Load environment configuration
load_dotenv()

SUPPORTED_EXTENSIONS = {
    ".pdf", ".epub", ".docx", ".doc", ".txt", ".mobi", ".azw3", ".rtf", ".fb2"
}


def format_size(bytes_val: int) -> str:
    """Format bytes into a human readable MB/KB string."""
    mb = bytes_val / (1024 * 1024)
    if mb < 0.01:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{mb:.2f} MB"


def scan_directory_for_books(books_dir: str) -> List[str]:
    """
    Recursively scan the target directory for all supported book files.
    """
    book_files = []
    if not os.path.exists(books_dir):
        return book_files

    for root, _, files in os.walk(books_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                full_path = os.path.join(root, file)
                book_files.append(full_path)

    return sorted(book_files)


def print_banner():
    """Print stylish terminal banner."""
    print("=" * 100)
    print(" 📚  KİTAP METAVERİ AYRIŞTIRICI, MYSQL SENKRONİZASYON VE RAPORLAMA SİSTEMİ  📚")
    print("=" * 100)


def display_results_table(books: List[Book], max_rows: int = 50):
    """
    Format and display the database records directly fetched from MySQL using tabulate.
    """
    total = len(books)
    display_list = books[:max_rows] if max_rows > 0 else books

    print("\n" + "=" * 100)
    print(f" 📋  MYSQL VERİTABANINDAN ÇEKİLEN KAYITLAR (Toplam: {total} Kayıt | Listelenen: {len(display_list)})")
    print("=" * 100)

    if not display_list:
        print(" Veritabanında gösterilecek kayıt bulunamadı.")
        return

    table_data = []
    for b in display_list:
        title_disp = (b.title[:30] + "..") if len(b.title) > 32 else b.title
        author_disp = (b.author[:20] + "..") if (b.author and len(b.author) > 22) else (b.author or "-")
        pages_disp = str(b.page_count) if b.page_count is not None else "-"
        type_disp = b.file_type.upper()
        size_disp = format_size(b.file_size_bytes)
        hash_disp = f"{b.sha256_hash[:8]}...{b.sha256_hash[-6:]}"
        path_disp = (b.file_path[:28] + "..") if len(b.file_path) > 30 else b.file_path

        table_data.append([
            b.id,
            title_disp,
            author_disp,
            pages_disp,
            type_disp,
            size_disp,
            hash_disp,
            path_disp
        ])

    headers = [
        "ID", "Kitap Adı", "Yazar", "Sayfa", "Tür", "Boyut", "SHA-256 Hash", "Dosya Lokasyonu"
    ]

    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid", stralign="left", numalign="right"))
    if total > len(display_list):
        print(f" ... ve {total - len(display_list)} kayıt daha veritabanında mevcut. (Tüm liste JSON ve CSV olarak kaydedildi)")


from zip_extractor import extract_all_zips_in_books


def run_scanner():
    """
    Main orchestration routine:
    1. Extracts all .zip archives in 'Books/' folder with Turkish character encoding support.
    2. Connects to MySQL and ensures 'library_db' database & 'books' table exist.
    3. Retrieves existing SHA-256 hashes for duplicate prevention.
    4. Scans 'Books/' folder recursively for all supported book formats.
    5. Extracts metadata, calculates SHA-256, and batch inserts new files into MySQL.
    6. Executes SELECT query directly on MySQL database.
    7. Displays tabular report via Tabulate.
    8. Exports records to 'books_from_db.json' and 'books_from_db.csv'.
    """
    print_banner()

    # Configuration
    books_dir = os.getenv("BOOKS_DIR", "Books")
    batch_size = int(os.getenv("BATCH_SIZE", "100"))
    db_cfg = get_db_config()

    print(f"📁 Hedef Klasör    : {os.path.abspath(books_dir)}")
    print(f"🗄️  Hedef Veritabanı: {db_cfg['user']}@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['database']}")
    print(f"📦 Toplu İşlem Boyu: {batch_size} kayıt/paket")
    print("-" * 100)

    # Step 1: Extract all ZIP files in Books directory
    print("\n[1/6] 📦 'Books/' klasöründeki .zip arşivleri kontrol ediliyor ve çıkarılıyor...")
    zip_summary = extract_all_zips_in_books(books_dir)

    # Step 2: Connect to MySQL and initialize database & schema
    print("\n[2/6] 🔌 MySQL Veritabanı ('library_db') kontrol ediliyor ve tablolar oluşturuluyor...")
    try:
        engine = get_engine()
        init_db(engine)
        session = get_session(engine)
        print("  ✓ MySQL bağlantısı başarılı. 'library_db.books' tablosu hazır.")
    except Exception as e:
        print(f"\n❌ Veritabanı Bağlantı Hatası: {e}")
        print("\n💡 İpuçları:")
        print("  1. MySQL servisinizin çalıştığından emin olun.")
        print("  2. '.env' dosyasındaki DB_HOST, DB_PORT, DB_USER, DB_PASSWORD ve DB_NAME ayarlarını kontrol edin.")
        print("  3. Gerekiyorsa ortam değişkenlerini güncelledikten sonra tekrar çalıştırın.\n")
        return

    # Step 3: Retrieve existing SHA-256 hashes to prevent duplicates
    print("\n[3/6] 🔍 Mevcut kayıtlar taranıyor (Mükerrer SHA-256 kontrolü)...")
    existing_hashes: Set[str] = get_existing_hashes(session)
    print(f"  ✓ Veritabanında {len(existing_hashes)} adet önceden kaydedilmiş benzersiz hash bulundu.")

    # Step 4: Scan directory for book files
    print(f"\n[4/6] 📂 '{books_dir}' klasörü tüm alt dizinleriyle taranıyor...")
    all_files = scan_directory_for_books(books_dir)
    print(f"  ✓ Toplam {len(all_files)} adet desteklenen kitap dosyası keşfedildi.")

    if not all_files:
        print(f"⚠️ '{books_dir}' klasöründe taranacak kitap dosyası bulunamadı.")
        session.close()
        return

    # Step 5: Extract metadata and perform batch insertions
    print("\n[5/6] ⚡ Metaveriler çıkarılıyor, SHA-256 hesaplanıyor ve MySQL'e kaydediliyor...")
    start_time = time.time()
    new_records_buffer = []
    new_added_count = 0
    skipped_count = 0
    seen_in_current_run: Set[str] = set()

    with tqdm(total=len(all_files), desc="İşleniyor", unit="dosya", ncols=95) as pbar:
        for file_path in all_files:
            try:
                # Extract metadata & 64KB SHA-256 hash
                metadata = extract_metadata(file_path, base_dir=os.getcwd())
                file_hash = metadata["sha256_hash"]

                # Check if hash already exists in DB or current run
                if file_hash in existing_hashes or file_hash in seen_in_current_run:
                    skipped_count += 1
                    pbar.set_postfix({"Yeni": new_added_count, "Atlanan": skipped_count})
                    pbar.update(1)
                    continue

                # Register hash
                seen_in_current_run.add(file_hash)
                new_records_buffer.append(metadata)

                # Batch insertion
                if len(new_records_buffer) >= batch_size:
                    saved = save_books_batch(session, new_records_buffer)
                    new_added_count += saved
                    for item in new_records_buffer:
                        existing_hashes.add(item["sha256_hash"])
                    new_records_buffer.clear()

                pbar.set_postfix({"Yeni": new_added_count, "Atlanan": skipped_count})
            except Exception:
                pass

            pbar.update(1)

        # Flush remaining buffer
        if new_records_buffer:
            saved = save_books_batch(session, new_records_buffer)
            new_added_count += saved
            for item in new_records_buffer:
                existing_hashes.add(item["sha256_hash"])
            new_records_buffer.clear()

    elapsed_time = round(time.time() - start_time, 2)
    print(f"\n  ✓ Veritabanı yazma tamamlandı: {new_added_count} yeni kitap eklendi, {skipped_count} mükerrer dosya atlandı. (Süre: {elapsed_time} sn)")

    # Step 6: Query MySQL database directly, display tabulate table, and export
    print("\n[6/6] 📊 MySQL Veritabanından veriler SELECT sorgusu ile çekiliyor ve listeleniyor...")
    try:
        all_books_from_db = get_all_books_from_db(session)
        display_results_table(all_books_from_db, max_rows=30)

        # Export to JSON & CSV
        json_file = export_to_json(all_books_from_db, "books_from_db.json")
        csv_file = export_to_csv(all_books_from_db, "books_from_db.csv")
        print(f"\n  💾 Veritabanı kayıtları dışa aktarıldı:")
        print(f"     • JSON: {json_file}")
        print(f"     • CSV : {csv_file}")
    except Exception as e:
        print(f"⚠️ Sonuçlar veritabanından çekilirken/listelenirken hata oluştu: {e}")
    finally:
        session.close()

    total_in_db = len(all_books_from_db) if 'all_books_from_db' in locals() else 'N/A'

    print("\n" + "=" * 100)
    print(f" ✨ İŞLEM ÖZETİ")
    print(f"   • Açılan ZIP Dosyası Sayısı     : {zip_summary['zip_count']}")
    print(f"   • ZIP'lerden Çıkarılan Dosyalar  : {zip_summary['extracted_count']}")
    print(f"   • Keşfedilen Toplam Dosya       : {len(all_files)}")
    print(f"   • Bu Çalıştırmada Eklenen Kitap : {new_added_count}")
    print(f"   • Mükerrer / Atlanan Dosya      : {skipped_count}")
    print(f"   • 🌟 GÜNCEL TOPLAM KİTAP SAYISI : {total_in_db}")
    print(f"   • Toplam Süre                   : {elapsed_time} saniye")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    run_scanner()


