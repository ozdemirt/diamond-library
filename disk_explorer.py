import os
import sys
import csv
import time
import argparse
from datetime import datetime

def format_size(size_bytes):
    """Format size in human-readable units."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"

def find_pdf_files(target_dir, csv_output_path="pdf_listesi.csv"):
    """
    Taranan dizindeki tüm PDF dosyalarını bulur,
    isimlerini ve dosya yollarını CSV dosyasına kaydeder.
    """
    abs_target_dir = os.path.abspath(target_dir)
    print("=" * 75)
    print(f"📄 PDF DOSYA TARAMASI BAŞLATILDI")
    print(f"📂 Taranan Dizin  : {abs_target_dir}")
    print(f"💾 Çıktı CSV Yolu : {os.path.abspath(csv_output_path)}")
    print("=" * 75 + "\n")

    pdf_records = []
    total_scanned_dirs = 0
    start_time = time.time()

    # Diskteki tüm alt klasörleri ve dosyaları tara
    for root, dirs, files in os.walk(abs_target_dir, followlinks=False):
        total_scanned_dirs += 1
        for file in files:
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(root, file)
                try:
                    stat = os.stat(full_path)
                    file_size = format_size(stat.st_size)
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    file_size = "Bilinmiyor"
                    mtime = "Bilinmiyor"

                pdf_records.append({
                    "Dosya Adı": file,
                    "Dosya Yolu": full_path,
                    "Bulunduğu Klasör": root,
                    "Boyut": file_size,
                    "Son Değiştirilme Tarihi": mtime
                })
                print(f" 📄 Bulundu #{len(pdf_records)}: {file}  -> {full_path}")

    elapsed_time = time.time() - start_time

    # CSV Dosyasına Yazma (Excel uyumluluğu için utf-8-sig)
    csv_file_abs = os.path.abspath(csv_output_path)
    try:
        with open(csv_file_abs, mode="w", newline="", encoding="utf-8-sig") as csv_file:
            fieldnames = ["Dosya Adı", "Dosya Yolu", "Bulunduğu Klasör", "Boyut", "Son Değiştirilme Tarihi"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(pdf_records)

        print("\n" + "=" * 75)
        print("✅ TARAMA BAŞARIYLA TAMAMLANDI VE CSV OLUŞTURULDU!")
        print(f"📊 Bulunan Toplam PDF Dosyası : {len(pdf_records)}")
        print(f"📁 Taranan Klasör Sayısı       : {total_scanned_dirs}")
        print(f"⏱️ Geçen Süre                  : {elapsed_time:.2f} saniye")
        print(f"💾 Oluşturulan CSV Dosyası     : {csv_file_abs}")
        print("=" * 75)
    except Exception as e:
        print(f"\n⚠️ CSV kaydedilirken bir hata oluştu: {e}")

def main():
    parser = argparse.ArgumentParser(description="Diskteki PDF Dosyalarını Bul ve İsimlerini/Yollarını CSV Olarak Kaydet")
    parser.add_argument("path", nargs="?", default=r"C:\Users\default.LAPTOP-OBA1HVU9", help="Taranacak dizin (Varsayılan: Kullanıcı Ana Klasörü)")
    parser.add_argument("-o", "--output", type=str, default="pdf_listesi.csv", help="Kaydedilecek CSV dosyasının adı (Varsayılan: pdf_listesi.csv)")

    args = parser.parse_args()
    find_pdf_files(args.path, csv_output_path=args.output)

if __name__ == "__main__":
    main()
