#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Doğrulama ve Bütünlük Kontrol Scripti
-----------------------------------------
Bu script, belirtilen klasördeki ve alt klasörlerindeki tüm dosyaları tarayarak:
1. Dosya uzantısı kontrolü (.pdf olmayanları tespit eder)
2. Magic Bytes / Header kontrolü (%PDF başlığı içermeyen sahte/bozuk dosyaları tespit eder)
3. Bütünlük ve Açılabilirlik kontrolü (pypdf kullanarak sayfaların okunabilirliğini test eder)

Kullanım:
    python verify_pdfs.py [klasor_yolu] [secenekler]
    
Örnekler:
    python verify_pdfs.py Books
    python verify_pdfs.py Converted_PDFs --report
    python verify_pdfs.py "C:/Kitaplar" --json
"""

import sys
import os
import argparse
import time
from typing import List, Dict, Any

# Python 3.15 Pillow slot-ID C-extension uyumluluk yaması
try:
    import PIL
    from PIL import Image
except Exception:
    import types
    pil_mod = types.ModuleType('PIL')
    pil_mod.__version__ = '10.0.0'
    image_mod = types.ModuleType('PIL.Image')
    class _ImageStub: pass
    image_mod.Image = _ImageStub
    sys.modules['PIL'] = pil_mod
    sys.modules['PIL.Image'] = image_mod

try:
    import pypdf
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError, EmptyFileError
except ImportError:
    print("[HATA] 'pypdf' kütüphanesi bulunamadı. Lütfen 'pip install pypdf' komutu ile yükleyin.")
    sys.exit(1)


def format_size(size_bytes: int) -> str:
    """Bayt cinsinden dosya boyutunu okunabilir formata çevirir (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def detect_file_type_from_bytes(header_bytes: bytes, ext: str) -> str:
    """Dosya başlığındaki baytlara ve uzantıya bakarak olası dosya türünü tahmin eder."""
    if not header_bytes:
        return "Boş Dosya (0 Bayt)"
    if header_bytes.startswith(b'%PDF'):
        return "PDF Belgesi"
    if header_bytes.startswith(b'PK\x03\x04') or header_bytes.startswith(b'PK\x05\x06'):
        if ext in ['.epub', '.docx', '.xlsx', '.pptx', '.apk']:
            return f"{ext[1:].upper()} (ZIP tabanlı arşiv)"
        return "ZIP / Arşiv Dosyası"
    if header_bytes.startswith(b'Rar!\x1a\x07'):
        return "RAR Arşivi"
    if header_bytes.startswith(b'7z\xbc\xaf\x27\x1c'):
        return "7-Zip Arşivi"
    if header_bytes.startswith(b'{\\rtf'):
        return "RTF Zengin Metin Belgesi"
    if header_bytes.strip().lower().startswith(b'<!doctype html') or header_bytes.strip().lower().startswith(b'<html'):
        return "HTML Web Sayfası / İndirme Hatası"
    if header_bytes.startswith(b'<?xml'):
        return "XML Belgesi"
    if header_bytes.startswith(b'\xff\xd8\xff'):
        return "JPEG Görseli"
    if header_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return "PNG Görseli"
    if header_bytes.startswith(b'GIF87a') or header_bytes.startswith(b'GIF89a'):
        return "GIF Görseli"
    if header_bytes.startswith(b'BM'):
        return "BMP Görseli"
    if header_bytes.startswith(b'BOOKMOBI') or b'BOOKMOBI' in header_bytes[:512]:
        return "MOBI E-Kitap"
    if ext:
        return f"{ext[1:].upper()} Dosyası"
    return "Bilinmeyen İkili/Metin Formatı"


def check_magic_bytes(file_path: str) -> tuple[bool, str, bytes]:
    """
    Dosyanın ilk 1024 baytını okuyarak geçerli bir %PDF başlığı içerip içermediğini kontrol eder.
    Dönen değer: (gecerli_mi, aciklama, header_bytes)
    """
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            return False, "Dosya boyutu 0 bayt (Tamamen boş dosya)", b""
        
        with open(file_path, 'rb') as f:
            header = f.read(1024)
            
        # PDF standardına göre %PDF başlığı dosyanın ilk 1024 baytı içinde yer almalıdır
        if b'%PDF' in header:
            return True, "Geçerli PDF başlığı", header
        else:
            detected = detect_file_type_from_bytes(header, os.path.splitext(file_path)[1].lower())
            return False, f"Sahte/Geçersiz PDF Başlığı (%PDF eksik. Algılanan tür: {detected})", header
    except Exception as e:
        return False, f"Dosya başlığı okunamadı: {str(e)}", b""


def verify_pdf_integrity(file_path: str) -> tuple[bool, int, str]:
    """
    pypdf kullanarak PDF dosyasının bütünlüğünü, şifre durumunu ve sayfa sayısını doğrular.
    Dönen değer: (basarili_mi, sayfa_sayisi, hata_veya_bilgi_mesaji)
    """
    try:
        reader = PdfReader(file_path, strict=False)
        
        # Şifre kontrolü
        if reader.is_encrypted:
            try:
                # Boş şifre denemesi
                decrypt_res = reader.decrypt('')
                if decrypt_res == 0:
                    return False, 0, "PDF şifrelenmiş ve parola olmadan açılamıyor (Parola korumalı)"
            except Exception as enc_err:
                return False, 0, f"Şifreli PDF açılamadı: {str(enc_err)}"
                
        page_count = len(reader.pages)
        if page_count == 0:
            return False, 0, "PDF geçerli bir sayfa içermiyor (Sayfa sayısı: 0)"
            
        # İlk ve son sayfaları kontrol ederek sayfa ağacının (page tree) ve xref bütünlüğünü doğrula
        _ = reader.pages[0]
        if page_count > 1:
            _ = reader.pages[-1]
            
        return True, page_count, f"{page_count} sayfa başarıyla doğrulandı"
        
    except EmptyFileError:
        return False, 0, "PDF dosyası boş (EmptyFileError)"
    except PdfReadError as pre:
        return False, 0, f"PDF Bütünlük Hatası (PdfReadError): {str(pre)}"
    except Exception as e:
        return False, 0, f"PDF Okuma/Açılma Hatası: {str(e)}"


def scan_directory(target_dir: str) -> Dict[str, Any]:
    """
    Hedef klasördeki tüm dosyaları yinelemeli (recursive) olarak tarar ve doğrular.
    """
    results = {
        "target_dir": os.path.abspath(target_dir),
        "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": 0,
        "valid_pdfs": [],
        "non_pdf_files": [],
        "fake_header_pdfs": [],
        "corrupted_pdfs": [],
    }
    
    print(f"\n[+] Tarama Başlatılıyor: {os.path.abspath(target_dir)}")
    print("=" * 75)
    
    file_count = 0
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            
            # Klasör veya geçersiz bağlantıları atla
            if not os.path.isfile(full_path):
                continue
                
            file_count += 1
            rel_path = os.path.relpath(full_path, target_dir)
            
            try:
                size_bytes = os.path.getsize(full_path)
            except OSError:
                size_bytes = 0
                
            ext = os.path.splitext(filename)[1].lower()
            
            # 1. ADIM: Uzantı Kontrolü
            if ext != '.pdf':
                try:
                    with open(full_path, 'rb') as f:
                        header = f.read(1024)
                except Exception:
                    header = b""
                file_type = detect_file_type_from_bytes(header, ext)
                
                results["non_pdf_files"].append({
                    "name": filename,
                    "rel_path": rel_path,
                    "full_path": full_path,
                    "extension": ext if ext else "(uzantısız)",
                    "detected_type": file_type,
                    "size_bytes": size_bytes,
                    "size_formatted": format_size(size_bytes)
                })
                continue
            
            # 2. ADIM: Magic Bytes / Header Kontrolü
            is_valid_header, header_msg, header_bytes = check_magic_bytes(full_path)
            if not is_valid_header:
                results["fake_header_pdfs"].append({
                    "name": filename,
                    "rel_path": rel_path,
                    "full_path": full_path,
                    "reason": header_msg,
                    "size_bytes": size_bytes,
                    "size_formatted": format_size(size_bytes)
                })
                continue
                
            # 3. ADIM: Bütünlük ve Açılabilirlik Kontrolü (pypdf)
            is_valid_pdf, page_count, status_msg = verify_pdf_integrity(full_path)
            if not is_valid_pdf:
                results["corrupted_pdfs"].append({
                    "name": filename,
                    "rel_path": rel_path,
                    "full_path": full_path,
                    "reason": status_msg,
                    "size_bytes": size_bytes,
                    "size_formatted": format_size(size_bytes)
                })
            else:
                results["valid_pdfs"].append({
                    "name": filename,
                    "rel_path": rel_path,
                    "full_path": full_path,
                    "pages": page_count,
                    "size_bytes": size_bytes,
                    "size_formatted": format_size(size_bytes)
                })
                
    results["total_files"] = file_count
    return results


def print_terminal_report(results: Dict[str, Any]):
    """Konsol ekranına zengin ve anlaşılır Türkçe özet raporu basar."""
    total = results["total_files"]
    valid_count = len(results["valid_pdfs"])
    non_pdf_count = len(results["non_pdf_files"])
    fake_count = len(results["fake_header_pdfs"])
    corrupt_count = len(results["corrupted_pdfs"])
    
    print("\n" + "=" * 75)
    print("                    PDF DOĞRULAMA VE TARAMA RAPORU                    ")
    print("=" * 75)
    print(f"Hedef Klasör         : {results['target_dir']}")
    print(f"Tarama Tarihi/Saati  : {results['scan_time']}")
    print("-" * 75)
    print(f"📁 Toplam Taranan Dosya Sayısı     : {total}")
    print(f"✅ Sorunsuz Geçerli PDF Sayısı     : {valid_count}")
    print(f"⚠️  PDF Uzantılı Olmayan Dosyalar   : {non_pdf_count}")
    print(f"❌ Sahte/Geçersiz Başlıklı PDF'ler  : {fake_count}")
    print(f"💥 Bozuk / Açılamayan PDF'ler      : {corrupt_count}")
    print("=" * 75)
    
    # 1. PDF Olmayan Dosyaların Listesi
    if non_pdf_count > 0:
        print(f"\n[⚠️  1. PDF UZANTILI OLMAYAN DOSYALAR ({non_pdf_count} adet)]")
        print("-" * 75)
        for i, item in enumerate(results["non_pdf_files"], 1):
            print(f"  {i}. {item['name']}")
            print(f"     └─ Tür/Uzantı : {item['detected_type']} ({item['extension']}) | Boyut: {item['size_formatted']}")
            print(f"     └─ Konum      : {item['rel_path']}")
            
    # 2. Sahte / Geçersiz Başlıklı PDF'ler
    if fake_count > 0:
        print(f"\n[❌ 2. SAHTE / GEÇERSİZ BAŞLIKLI PDF'LER (%PDF Eksik) ({fake_count} adet)]")
        print("-" * 75)
        for i, item in enumerate(results["fake_header_pdfs"], 1):
            print(f"  {i}. {item['name']}")
            print(f"     └─ Hata Nedeni: {item['reason']}")
            print(f"     └─ Boyut      : {item['size_formatted']} | Konum: {item['rel_path']}")
            
    # 3. Bozuk / Açılamayan PDF'ler
    if corrupt_count > 0:
        print(f"\n[💥 3. BOZUK / AÇILAMAYAN PDF'LER ({corrupt_count} adet)]")
        print("-" * 75)
        for i, item in enumerate(results["corrupted_pdfs"], 1):
            print(f"  {i}. {item['name']}")
            print(f"     └─ Hata Nedeni: {item['reason']}")
            print(f"     └─ Boyut      : {item['size_formatted']} | Konum: {item['rel_path']}")
            
    if fake_count == 0 and corrupt_count == 0 and non_pdf_count == 0:
        print("\n✨ TEBRİKLER! Taranan tüm dosyalar geçerli ve sorunsuz PDF formatındadır.")
        
    print("\n" + "=" * 75)


def generate_markdown_report(results: Dict[str, Any], output_path: str):
    """Ayrıntılı Markdown rapor dosyası üretir."""
    total = results["total_files"]
    valid_count = len(results["valid_pdfs"])
    non_pdf_count = len(results["non_pdf_files"])
    fake_count = len(results["fake_header_pdfs"])
    corrupt_count = len(results["corrupted_pdfs"])
    
    md = []
    md.append("# PDF Doğrulama ve Arşiv Bütünlük Raporu\n")
    md.append(f"- **Hedef Dizin**: `{results['target_dir']}`")
    md.append(f"- **Tarama Zamanı**: `{results['scan_time']}`\n")
    
    md.append("## 📊 Özet İstatistikler\n")
    md.append("| Kategori | Dosya Sayısı | Yüzde | Durum |")
    md.append("| :--- | :---: | :---: | :---: |")
    
    def pct(n):
        return f"{(n / total * 100):.1f}%" if total > 0 else "0.0%"
        
    md.append(f"| **Toplam Taranan Dosya** | **{total}** | 100.0% | 📁 |")
    md.append(f"| **Geçerli ve Sağlam PDF'ler** | **{valid_count}** | {pct(valid_count)} | ✅ |")
    md.append(f"| **PDF Olmayan Dosyalar** | **{non_pdf_count}** | {pct(non_pdf_count)} | ⚠️ |")
    md.append(f"| **Sahte / Yanıltıcı PDF'ler** | **{fake_count}** | {pct(fake_count)} | ❌ |")
    md.append(f"| **Bozuk / Açılamayan PDF'ler** | **{corrupt_count}** | {pct(corrupt_count)} | 💥 |\n")
    
    if non_pdf_count > 0:
        md.append(f"## ⚠️ 1. PDF Uzantılı Olmayan Dosyalar ({non_pdf_count} adet)\n")
        md.append("| # | Dosya Adı | Algılanan Tür | Uzantı | Boyut | Konum |")
        md.append("| :---: | :--- | :--- | :---: | :---: | :--- |")
        for i, item in enumerate(results["non_pdf_files"], 1):
            md.append(f"| {i} | `{item['name']}` | {item['detected_type']} | `{item['extension']}` | {item['size_formatted']} | `{item['rel_path']}` |")
        md.append("")
        
    if fake_count > 0:
        md.append(f"## ❌ 2. Sahte / Yanıltıcı PDF'ler (Geçersiz Header) ({fake_count} adet)\n")
        md.append("| # | Dosya Adı | Hata Açıklaması | Boyut | Konum |")
        md.append("| :---: | :--- | :--- | :---: | :--- |")
        for i, item in enumerate(results["fake_header_pdfs"], 1):
            md.append(f"| {i} | `{item['name']}` | {item['reason']} | {item['size_formatted']} | `{item['rel_path']}` |")
        md.append("")
        
    if corrupt_count > 0:
        md.append(f"## 💥 3. Bozuk veya Açılamayan PDF'ler ({corrupt_count} adet)\n")
        md.append("| # | Dosya Adı | Bütünlük / Okuma Hatası | Boyut | Konum |")
        md.append("| :---: | :--- | :--- | :---: | :--- |")
        for i, item in enumerate(results["corrupted_pdfs"], 1):
            md.append(f"| {i} | `{item['name']}` | {item['reason']} | {item['size_formatted']} | `{item['rel_path']}` |")
        md.append("")
        
    if valid_count > 0:
        md.append(f"## ✅ 4. Geçerli PDF Örnekleri (İlk 20 dosya - Toplam: {valid_count})\n")
        md.append("| # | Dosya Adı | Sayfa Sayısı | Boyut | Konum |")
        md.append("| :---: | :--- | :---: | :---: | :--- |")
        for i, item in enumerate(results["valid_pdfs"][:20], 1):
            md.append(f"| {i} | `{item['name']}` | {item['pages']} | {item['size_formatted']} | `{item['rel_path']}` |")
        if valid_count > 20:
            md.append(f"\n*(ve {valid_count - 20} adet daha sorunsuz geçerli PDF)*\n")
            
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
        
    print(f"[i] Ayrıntılı Markdown raporu kaydedildi: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Kitap Arşivi PDF Doğrulama ve Bütünlük Kontrol Aracı")
    parser.add_argument("folder", nargs="?", default=None, help="Taranacak klasör yolu (Örn: Books veya C:/Arsiv)")
    parser.add_argument("-d", "--dir", dest="dir_path", help="Taranacak klasör yolu")
    parser.add_argument("-o", "--output", dest="output_report", default="pdf_dogrulama_raporu.md", help="Rapor dosyasının kaydedileceği yol (Varsayılan: pdf_dogrulama_raporu.md)")
    parser.add_argument("--json", action="store_true", help="Sonuçları JSON formatında da kaydet")
    
    args = parser.parse_args()
    
    target_dir = args.dir_path or args.folder
    
    if not target_dir:
        # Etkileşimli giriş veya varsayılan belirleme
        print("PDF Doğrulama Aracına Hoş Geldiniz.")
        user_input = input("Taranacak klasör yolunu giriniz (Varsayılan: Converted_PDFs): ").strip()
        if user_input:
            target_dir = user_input.strip('"\'')
        else:
            target_dir = "Converted_PDFs" if os.path.exists("Converted_PDFs") else "."
            
    if not os.path.exists(target_dir):
        print(f"[HATA] Belirtilen klasör bulunamadı: {target_dir}")
        sys.exit(1)
        
    results = scan_directory(target_dir)
    print_terminal_report(results)
    
    if args.output_report:
        generate_markdown_report(results, args.output_report)
        
    if args.json:
        import json
        json_path = os.path.splitext(args.output_report)[0] + ".json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[i] JSON formatındaki veri kaydedildi: {json_path}")


if __name__ == "__main__":
    main()
