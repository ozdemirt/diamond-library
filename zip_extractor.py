"""
ZIP Archive Extractor Module for Book Collections.
Extracts all .zip archives in 'Books/' into their respective directories,
properly handling Turkish character encodings (UTF-8 / CP1254 / CP437) and Windows paths.
"""

import os
import sys
import zipfile
from typing import List, Tuple, Dict, Any
from tqdm import tqdm


def decode_zip_filename(info: zipfile.ZipInfo) -> str:
    """
    Properly decode zip entry filename handling UTF-8, CP1254, CP437 encodings.
    """
    raw_name = info.filename
    # If UTF-8 flag bit is set
    if info.flag_bits & 0x800:
        return raw_name

    # Try decoding from CP437 bytes
    try:
        raw_bytes = raw_name.encode('cp437')
    except Exception:
        return raw_name

    # Try UTF-8 first
    try:
        return raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        pass

    # Try Turkish Windows-1254
    try:
        return raw_bytes.decode('cp1254')
    except UnicodeDecodeError:
        pass

    # Fallback to Latin-1
    try:
        return raw_bytes.decode('latin1')
    except UnicodeDecodeError:
        return raw_name


def safe_extract_zip(zip_path: str, target_dir: str) -> Tuple[int, int]:
    """
    Safely extract a single zip file to target_dir.
    Returns (extracted_count, skipped_count).
    """
    os.makedirs(target_dir, exist_ok=True)
    extracted = 0
    skipped = 0

    with zipfile.ZipFile(zip_path, 'r') as zf:
        infolist = [i for i in zf.infolist() if not i.is_dir()]

        for info in infolist:
            decoded_rel_path = decode_zip_filename(info)
            # Normalize slashes
            decoded_rel_path = decoded_rel_path.replace("\\", "/").lstrip("/")

            target_file_path = os.path.join(target_dir, *decoded_rel_path.split("/"))
            
            # Windows long path handling if needed
            abs_target = os.path.abspath(target_file_path)
            if os.name == 'nt' and len(abs_target) >= 240 and not abs_target.startswith("\\\\?\\"):
                win_path = "\\\\?\\" + abs_target
            else:
                win_path = abs_target

            # Skip if already exists and size matches
            if os.path.exists(win_path):
                try:
                    if os.path.getsize(win_path) == info.file_size:
                        skipped += 1
                        continue
                except Exception:
                    pass

            # Create parent directory
            parent_dir = os.path.dirname(win_path)
            os.makedirs(parent_dir, exist_ok=True)

            # Extract file content
            try:
                with zf.open(info) as src, open(win_path, "wb") as dst:
                    while chunk := src.read(128 * 1024):
                        dst.write(chunk)
                extracted += 1
            except Exception as e:
                # Fallback extraction
                try:
                    data = zf.read(info)
                    with open(win_path, "wb") as dst:
                        dst.write(data)
                    extracted += 1
                except Exception as ex:
                    print(f"  ⚠️ Çıkarma hatası ({decoded_rel_path}): {ex}")

    return extracted, skipped


def extract_all_zips_in_books(books_dir: str = "Books") -> Dict[str, Any]:
    """
    Find all .zip files in books_dir, extract each to Books/<archive_name>/
    and return detailed summary statistics.
    """
    if not os.path.exists(books_dir):
        return {"zip_count": 0, "extracted_count": 0, "skipped_count": 0, "details": []}

    zip_files = []
    for f in os.listdir(books_dir):
        if f.lower().endswith(".zip"):
            full_path = os.path.join(books_dir, f)
            if os.path.isfile(full_path):
                zip_files.append(full_path)

    zip_files = sorted(zip_files)
    total_zips = len(zip_files)
    total_extracted = 0
    total_skipped = 0
    details = []

    print(f"\n📦 Toplam {total_zips} adet .zip arşivi tespit edildi.")
    print("=" * 80)

    for idx, zip_path in enumerate(zip_files, 1):
        zip_filename = os.path.basename(zip_path)
        base_name, _ = os.path.splitext(zip_filename)
        target_dir = os.path.join(books_dir, base_name)
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)

        print(f"[{idx}/{total_zips}] 📂 Arşiv Açılıyor: {zip_filename} ({zip_size_mb:.1f} MB)...")
        ext_count, skip_count = safe_extract_zip(zip_path, target_dir)
        total_extracted += ext_count
        total_skipped += skip_count

        print(f"       ↳ {ext_count} dosya yeni çıkarıldı, {skip_count} dosya zaten mevcuttu.")
        details.append({
            "archive": zip_filename,
            "target_dir": target_dir,
            "extracted": ext_count,
            "skipped": skip_count
        })

    print("=" * 80)
    print(f" ✓ Tüm arşivler açıldı: {total_extracted} yeni dosya çıkarıldı, {total_skipped} dosya atlandı.\n")

    return {
        "zip_count": total_zips,
        "extracted_count": total_extracted,
        "skipped_count": total_skipped,
        "details": details
    }


if __name__ == "__main__":
    extract_all_zips_in_books("Books")
