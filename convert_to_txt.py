"""
High-Performance Multi-Threaded PDF and EPUB to Plain Text (.txt) Converter.
Uses 12 concurrent workers to scan and extract clean text from all books in 'Books/',
strips HTML/CSS markup, preserves Turkish characters, saves UTF-8 text files in 'converted_texts/',
and generates detailed page/word count reports and unreadable file audits.
"""

import os
import re
import csv
import json
import time
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any, Optional
import pymupdf
from bs4 import BeautifulSoup
from tqdm import tqdm
from tabulate import tabulate


def calculate_sha256(file_path: str, chunk_size: int = 64 * 1024) -> str:
    """Calculate 64KB chunk SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


def clean_text_content(text: str) -> str:
    """
    Clean up whitespace, non-printable characters, and multiple blank lines
    while strictly preserving paragraphs and Turkish characters.
    """
    if not text:
        return ""
    text = text.replace('\xa0', ' ').replace('\u200b', '').replace('\ufeff', '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_text_from_pdf(file_path: str) -> Tuple[str, int, int, int, str]:
    """
    Extract text from a PDF file page-by-page.
    Returns (full_text, page_count, word_count, char_count, status).
    """
    doc = None
    try:
        doc = pymupdf.open(file_path)
        page_count = len(doc)
        if page_count == 0:
            return "", 0, 0, 0, "Boş Belge (0 Sayfa)"

        extracted_pages = []
        total_words = 0
        total_chars = 0

        for page_num in range(page_count):
            page = doc[page_num]
            page_text = page.get_text("text")
            cleaned_page = clean_text_content(page_text)

            if cleaned_page:
                extracted_pages.append(f"--- Sayfa {page_num + 1} ---\n{cleaned_page}")
                words = len(cleaned_page.split())
                total_words += words
                total_chars += len(cleaned_page)

        full_text = "\n\n".join(extracted_pages)

        if total_words == 0:
            status = "Görsel / Taranmış (0 Kelime)"
        else:
            status = "Başarılı"

        return full_text, page_count, total_words, total_chars, status
    except Exception as e:
        return "", 0, 0, 0, f"Hata: {str(e)[:100]}"
    finally:
        if doc:
            try:
                doc.close()
            except Exception:
                pass


def extract_text_from_epub(file_path: str) -> Tuple[str, int, int, int, str]:
    """
    Extract text from an EPUB file, stripping all HTML/CSS tags cleanly.
    Returns (full_text, page_count, word_count, char_count, status).
    """
    doc = None
    try:
        doc = pymupdf.open(file_path)
        page_count = len(doc)
        extracted_pages = []
        total_words = 0
        total_chars = 0

        for page_num in range(page_count):
            page = doc[page_num]
            page_text = page.get_text("text")
            cleaned_page = clean_text_content(page_text)

            if cleaned_page:
                extracted_pages.append(f"--- Bölüm/Sayfa {page_num + 1} ---\n{cleaned_page}")
                words = len(cleaned_page.split())
                total_words += words
                total_chars += len(cleaned_page)

        full_text = "\n\n".join(extracted_pages)

        if total_words == 0:
            status = "Görsel / Metinsiz EPUB"
        else:
            status = "Başarılı"

        return full_text, page_count, total_words, total_chars, status
    except Exception as e:
        return "", 0, 0, 0, f"Hata: {str(e)[:100]}"
    finally:
        if doc:
            try:
                doc.close()
            except Exception:
                pass


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid Windows characters."""
    invalid_chars = r'[\\/*?:"<>|]'
    clean_name = re.sub(invalid_chars, '_', filename)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    return clean_name


def process_single_book(task: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    """
    Worker function to process and convert a single book to TXT.
    """
    full_path = task["full_path"]
    ext = task["ext"]
    txt_filename = task["txt_filename"]
    rel_path = task["rel_path"]
    file_hash = task["sha256_hash"]

    txt_path = os.path.join(output_dir, txt_filename)

    if ext == '.pdf':
        content, pages, words, chars, status = extract_text_from_pdf(full_path)
    else:
        content, pages, words, chars, status = extract_text_from_epub(full_path)

    if status == "Başarılı":
        try:
            with open(txt_path, "w", encoding="utf-8") as f_out:
                f_out.write(content)
        except Exception as ex:
            status = f"Yazma Hatası: {ex}"
    elif "Görsel" in status:
        try:
            with open(txt_path, "w", encoding="utf-8") as f_out:
                f_out.write(f"[BİLGİ: Bu {ext.upper()} belgesi yalnızca taranmış görsellerden oluşmaktadır ve metin katmanı bulunmamaktadır.]\n")
        except Exception:
            pass

    return {
        "dosya_adi": os.path.basename(full_path),
        "kaynak_yol": rel_path,
        "txt_dosyasi": txt_filename,
        "format": ext.upper().replace(".", ""),
        "sayfa_sayisi": pages,
        "kelime_sayisi": words,
        "karakter_sayisi": chars,
        "durum": status,
        "sha256_hash": file_hash or "-"
    }


def run_batch_conversion(
    books_dir: str = "Books",
    output_dir: str = "converted_texts",
    max_workers: int = 12
):
    print("=" * 95)
    print(" 📖  PDF VE EPUB KİTAPLARINI TEMİZ TXT FORMATINA DÖNÜŞTÜRME SİSTEMİ  📖")
    print("=" * 95)

    os.makedirs(output_dir, exist_ok=True)

    # 1. Discover all PDF and EPUB files
    print(f"\n[1/4] 🔍 '{books_dir}' klasöründeki tüm PDF ve EPUB dosyaları taranıyor...")
    all_disk_files = []
    for root, _, files in os.walk(books_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.pdf', '.epub'):
                full_path = os.path.join(root, f)
                all_disk_files.append((full_path, ext))

    all_disk_files.sort(key=lambda x: x[0])
    total_files = len(all_disk_files)
    pdf_count = sum(1 for _, ext in all_disk_files if ext == '.pdf')
    epub_count = sum(1 for _, ext in all_disk_files if ext == '.epub')

    print(f"  ✓ Toplam {total_files} adet dosya tespit edildi: {pdf_count} PDF, {epub_count} EPUB.")
    print(f"  📁 Çıktı Klasörü: {os.path.abspath(output_dir)}")
    print(f"  🚀 Paralel İşlemci: {max_workers} İş Parçacığı (Threads)")
    print("-" * 95)

    # 2. Fast Deduplication & Task Preparation
    print(f"\n[2/4] ⚡ Dosyalar tekilleştiriliyor ve dönüştürme görevleri hazırlanıyor...")
    seen_hashes: Dict[str, str] = {}  # sha256 -> txt_filename
    used_filenames: Dict[str, int] = {}
    
    unique_tasks: List[Dict[str, Any]] = []
    duplicate_results: List[Dict[str, Any]] = []

    for full_path, ext in tqdm(all_disk_files, desc="Hazırlanıyor", unit="dosya", ncols=90):
        filename = os.path.basename(full_path)
        base_name, _ = os.path.splitext(filename)
        rel_path = os.path.relpath(full_path, os.getcwd()).replace("\\", "/")

        try:
            file_hash = calculate_sha256(full_path)
        except Exception:
            file_hash = None

        # If duplicate hash already registered
        if file_hash and file_hash in seen_hashes:
            duplicate_results.append({
                "dosya_adi": filename,
                "kaynak_yol": rel_path,
                "txt_dosyasi": seen_hashes[file_hash],
                "format": ext.upper().replace(".", ""),
                "sayfa_sayisi": 0,
                "kelime_sayisi": 0,
                "karakter_sayisi": 0,
                "durum": "Mükerrer (Atlandı)",
                "sha256_hash": file_hash
            })
            continue

        # Generate unique TXT filename
        clean_base = sanitize_filename(base_name) or "isimsiz_kitap"
        lower_base = clean_base.lower()
        if lower_base in used_filenames:
            used_filenames[lower_base] += 1
            txt_filename = f"{clean_base}_{used_filenames[lower_base]}.txt"
        else:
            used_filenames[lower_base] = 1
            txt_filename = f"{clean_base}.txt"

        if file_hash:
            seen_hashes[file_hash] = txt_filename

        unique_tasks.append({
            "full_path": full_path,
            "ext": ext,
            "txt_filename": txt_filename,
            "rel_path": rel_path,
            "sha256_hash": file_hash
        })

    print(f"  ✓ {len(unique_tasks)} adet benzersiz kitap dönüştürülecek, {len(duplicate_results)} mükerrer kopya atlandı.")

    # 3. Multi-Threaded Conversion
    print(f"\n[3/4] ⚡ {max_workers} iş parçacığı ile metin ayıklama başlatılıyor...")
    start_time = time.time()
    converted_results: List[Dict[str, Any]] = []

    success_count = 0
    image_only_count = 0
    error_count = 0
    total_pages_all = 0
    total_words_all = 0

    lock = threading.Lock()

    with tqdm(total=len(unique_tasks), desc="Dönüştürülüyor", unit="kitap", ncols=95) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_single_book, task, output_dir) for task in unique_tasks]
            
            for future in as_completed(futures):
                try:
                    res = future.result()
                    converted_results.append(res)
                    
                    with lock:
                        if res["durum"] == "Başarılı":
                            success_count += 1
                            total_pages_all += res["sayfa_sayisi"]
                            total_words_all += res["kelime_sayisi"]
                        elif "Görsel" in res["durum"]:
                            image_only_count += 1
                            total_pages_all += res["sayfa_sayisi"]
                        else:
                            error_count += 1

                        pbar.set_postfix({
                            "Başarılı": success_count,
                            "Görsel": image_only_count,
                            "Hata": error_count
                        })
                except Exception as ex:
                    with lock:
                        error_count += 1
                
                pbar.update(1)

    elapsed_time = round(time.time() - start_time, 2)
    all_results = converted_results + duplicate_results

    print(f"\n  ✓ Dönüştürme tamamlandı: {success_count} kitap başarıyla TXT'ye çevrildi. (Süre: {elapsed_time} sn)")

    # 4. Export Summary JSON and CSV
    print(f"\n[4/4] 💾 Özet rapor dosyaları hazırlanıyor ve kaydediliyor...")
    json_path = "converted_texts_summary.json"
    csv_path = "converted_texts_summary.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "toplam_dosya": total_files,
            "benzersiz_kitap_sayisi": len(unique_tasks),
            "basarili_donusturulen": success_count,
            "gorsel_taranmis_dosyalar": image_only_count,
            "mukerrer_atlanan": len(duplicate_results),
            "hata_veren": error_count,
            "toplam_sayfa": total_pages_all,
            "toplam_kelime": total_words_all,
            "toplam_sure_saniye": elapsed_time,
            "detaylar": all_results
        }, f, ensure_ascii=False, indent=2)

    csv_fields = [
        "dosya_adi", "kaynak_yol", "txt_dosyasi", "format",
        "sayfa_sayisi", "kelime_sayisi", "karakter_sayisi", "durum", "sha256_hash"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    print(f"  ✓ JSON Raporu: {os.path.abspath(json_path)}")
    print(f"  ✓ CSV Raporu : {os.path.abspath(csv_path)}")

    # 5. Display Terminal Tabulate Report
    print("\n" + "=" * 95)
    print(" 📊  DÖNÜŞTÜRME VE METİN DENETİM SONUÇLARI")
    print("=" * 95)

    summary_kpi_table = [
        ["1. Taranan Toplam Kitap Dosyası", total_files],
        ["   ↳ PDF Dosyaları", pdf_count],
        ["   ↳ EPUB Dosyaları", epub_count],
        ["2. Benzersiz Kitap Sayısı (İşlenen)", len(unique_tasks)],
        ["3. Başarıyla Dönüştürülen TXT Kitap Sayısı", success_count],
        ["4. Görsel / Taranmış (Metin Katmanı Olmayan) Kitaplar", image_only_count],
        ["5. Mükerrer (Kopya) Olduğu İçin Atlanan Dosyalar", len(duplicate_results)],
        ["6. Hata Veren / Açılamayan Dosyalar", error_count],
        ["7. Çıkarılan Toplam Sayfa Sayısı", f"{total_pages_all:,}"],
        ["8. Çıkarılan Toplam Kelime Sayısı", f"{total_words_all:,}"],
        ["9. Toplam İşlem Süresi", f"{elapsed_time} saniye"]
    ]
    print(tabulate(summary_kpi_table, headers=["Metrik", "Değer"], tablefmt="fancy_grid", numalign="right"))

    # Sample Converted Books Table
    sample_successful = [r for r in converted_results if r["durum"] == "Başarılı"][:10]
    sample_table = []
    for s in sample_successful:
        t_name = (s["txt_dosyasi"][:36] + "..") if len(s["txt_dosyasi"]) > 38 else s["txt_dosyasi"]
        sample_table.append([
            t_name,
            s["format"],
            s["sayfa_sayisi"],
            f"{s['kelime_sayisi']:,}",
            f"{s['karakter_sayisi']:,}",
            s["durum"]
        ])

    print("\n📋 DÖNÜŞTÜRÜLEN KİTAPLARDAN ÖRNEK 10 KAYIT:")
    print(tabulate(
        sample_table,
        headers=["TXT Dosya Adı", "Format", "Sayfa", "Kelime Sayısı", "Karakter Sayısı", "Durum"],
        tablefmt="fancy_grid",
        stralign="left",
        numalign="right"
    ))

    # Unreadable / Image-only files table if any
    unreadable_files = [r for r in converted_results if "Görsel" in r["durum"] or "Hata" in r["durum"]]
    if unreadable_files:
        print(f"\n⚠️ METİN İÇERMEYEN / GÖRSEL TARANMIŞ PDF'LER (Toplam {len(unreadable_files)} Dosya):")
        unreadable_table = []
        for u in unreadable_files[:10]:
            u_name = (u["dosya_adi"][:40] + "..") if len(u["dosya_adi"]) > 42 else u["dosya_adi"]
            unreadable_table.append([u_name, u["format"], u["sayfa_sayisi"], u["durum"]])
        print(tabulate(
            unreadable_table,
            headers=["Dosya Adı", "Format", "Sayfa", "Durum"],
            tablefmt="fancy_grid",
            stralign="left"
        ))
        if len(unreadable_files) > 10:
            print(f"  ... ve {len(unreadable_files) - 10} dosya daha (Tam liste 'converted_texts_summary.csv' dosyasında).")

    print("\n" + "=" * 95 + "\n")


if __name__ == "__main__":
    run_batch_conversion("Books", "converted_texts", max_workers=12)
