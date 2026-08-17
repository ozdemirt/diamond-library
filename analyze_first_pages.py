import os
import re
import zlib
import zipfile
import csv
import time

def tr_to_ascii(text):
    mapping = {
        'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U', 'ş': 's', 'Ş': 'S',
        'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C',
        '’': "'", '‘': "'", '“': '"', '”': '"',
        '–': '-', '—': '-', '…': '...'
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text

def detect_language(text, filename=""):
    if not text or len(text.strip()) < 5:
        if any(k in filename.lower() for k in ['english', '-eng', '_eng', 'vol-']):
            return 'İngilizce'
        return 'Türkçe'

    if re.search(r'[\u0600-\u06FF]', text):
        return 'Arapça'

    text_lower = text.lower()

    tr_words = {'ve', 'bir', 'bu', 'ile', 'için', 'da', 'de', 'olarak', 'göre', 'olan', 'sayı', 'yayınları', 'dergisi', 'gibi', 'sonra', 'tarafından', 'kitabı', 'bölüm'}
    en_words = {'the', 'and', 'of', 'to', 'in', 'is', 'that', 'for', 'with', 'as', 'by', 'on', 'this', 'are', 'from', 'or', 'at', 'an', 'chapter', 'book', 'history'}
    de_words = {'und', 'die', 'der', 'das', 'ist', 'in', 'von', 'mit', 'auf', 'für', 'buch'}

    words = set(re.findall(r'\b[a-zA-ZçğıöşüÇĞİÖŞÜ]+\b', text_lower))

    tr_score = len(words.intersection(tr_words))
    en_score = len(words.intersection(en_words))
    de_score = len(words.intersection(de_words))

    if 'Books for Text_Eng' in filename or 'Eng' in filename:
        en_score += 3

    if tr_score > en_score and tr_score > de_score:
        return 'Türkçe'
    elif en_score > tr_score and en_score > de_score:
        return 'İngilizce'
    elif de_score > tr_score and de_score > en_score:
        return 'Almanca'
    elif tr_score > 0:
        return 'Türkçe'
    elif en_score > 0:
        return 'İngilizce'

    return 'Türkçe'

def detect_author(filename, folder, text_preview):
    path = (folder + "/" + filename).replace('\\', '/')
    name = filename.strip()
    name_lower = name.lower()

    # Search in text preview first
    match_preview = re.search(r'(?:yazar|author|yazan)\s*:\s*([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)+)', text_preview, re.IGNORECASE)
    if match_preview:
        return match_preview.group(1).strip()

    if any(k in path for k in ['/Suat Yıldırım/', '/Suat Yildirim/', 'Suat Yildirim', 'Suat Yıldırım']):
        return 'Suat Yıldırım'
    if any(k in path for k in ['/Hekimoğlu İsmail/', 'Hekimoğlu', 'Hekimoglu']):
        return 'Hekimoğlu İsmail'
    if any(k in path for k in ['/MFG/', '/PRL-English/', 'Fethullah', 'Gulen', 'Fasildan-Fasila', 'Kalbin-Zumrut', 'Inancin-Golgesinde']):
        return 'M. Fethullah Gülen'
    if any(k in path for k in ['Necmettin-Sahiner', 'Necmeddin-Şahiner', 'Sahiner', 'Necmeddin Şahiner']):
        return 'Necmeddin Şahiner'
    if ('Davut' in name and ('Aydüz' in name or 'Ayduz' in name)) or 'Davut Aydüz' in path:
        return 'Davut Aydüz'
    if 'Vehbe Zuhayli' in name or 'Zuhayli' in name or 'vehbe-zuhayli' in name_lower:
        return 'Vehbe Zuhayli'
    if 'Ali Unal' in name or 'ali-unal' in name_lower or 'Ali Ünal' in name:
        return 'Ali Ünal'
    if 'Aytunc Altindal' in name or 'aytunc-altindal' in name_lower or 'Aytunç Altındal' in name:
        return 'Aytunç Altındal'
    if 'Reşid Haylamaz' in path or 'Haylamaz' in path or 'haylamaz' in name_lower:
        return 'Reşit Haylamaz'
    if 'Mehmet Akar' in path or 'mehmet-akar' in name_lower:
        return 'Mehmet Akar'
    if 'Umberto Eco' in name or 'umberto-eco' in name_lower:
        return 'Umberto Eco'
    if 'İbrahim Canan' in name or 'ibrahim-canan' in name_lower:
        return 'İbrahim Canan'
    if 'rabia-kandira' in name_lower:
        return 'Rabia Kandıra'
    if 'osman-kaplan' in name_lower:
        return 'Osman Kaplan'
    if 'safak-demir' in name_lower:
        return 'Şafak Demir'
    if 'h-ibrahim-cayirli' in name_lower or 'ibrahim-cayirli' in name_lower:
        return 'H. İbrahim Çayırlı'
    if 'aysel-ertan' in name_lower:
        return 'Aysel Ertan'
    if 'ayhan-tekines' in name_lower or 'Ayhan Tekineş' in path:
        return 'Ayhan Tekineş'
    if 'Arif Sarsılmaz' in path or 'sarsilmaz' in name_lower:
        return 'Arif Sarsılmaz'

    match = re.match(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)+)\s*-\s*', name)
    if match:
        cand = match.group(1).strip()
        if len(cand) > 4 and cand not in ['Mesnevi Hikayelerinden', 'Final sample', 'Lab and', 'Kuresel Dunyada', 'Untitled document']:
            return cand

    return 'Çeşitli / Belirtilmemiş'

def parse_pdf_bytes(data):
    """Extract page count and text preview from raw PDF bytes."""
    pages_matches = re.findall(rb'/Type\s*/Page\b', data)
    page_count = len(pages_matches) or 1

    streams = re.findall(rb'stream\r?\n(.*?)\r?\nendstream', data, re.DOTALL)
    extracted_text = []

    for s in streams[:15]:
        decomp = s
        try:
            decomp = zlib.decompress(s)
        except Exception:
            pass

        text_matches = re.findall(rb'\((.*?)\)\s*Tj|\((.*?)\)\s*T\*', decomp)
        for m in text_matches:
            t = (m[0] or m[1]).decode('latin1', 'ignore')
            clean_t = t.strip()
            if len(clean_t) > 1 and not clean_t.startswith('/'):
                extracted_text.append(clean_t)

    preview = ' '.join(extracted_text[:60])
    return page_count, preview

def analyze_all_books(books_dir=r"C:\Users\default.LAPTOP-OBA1HVU9\.antigravity-ide\Books",
                      csv_output="kitaplar_sayfa_analizi.csv"):
    target_dir = os.path.abspath(books_dir)
    csv_path = os.path.abspath(csv_output)

    print("=" * 75)
    print("📖 KİTAPLARIN 1., 2. VE 3. SAYFA ANALİZİ BAŞLATILDI")
    print(f"📁 Taranan Klasör : {target_dir}")
    print(f"💾 Çıktı CSV      : {csv_path}")
    print("=" * 75 + "\n")

    results = []
    supported_exts = {'.pdf', '.epub', '.mobi', '.txt', '.doc', '.docx'}
    start_time = time.time()
    processed_count = 0

    for root, dirs, files in os.walk(target_dir):
        for file in files:
            full_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()

            if ext == '.pdf':
                processed_count += 1
                try:
                    with open(full_path, 'rb') as f:
                        data = f.read()
                    page_count, preview = parse_pdf_bytes(data)
                except Exception as e:
                    page_count, preview = 1, f"Okuma hatası: {e}"

                lang = detect_language(preview, full_path)
                author = detect_author(file, root, preview)
                clean_preview = preview[:250].strip() or "(Görsel veya Özel Sayfa İçeriği)"

                results.append({
                    "Kitap Adı": file,
                    "Yazar": author,
                    "Dil": lang,
                    "Sayfa Sayısı": page_count,
                    "1.-3. Sayfa Özeti": clean_preview,
                    "Format": "PDF",
                    "Tam Dosya Yolu": full_path
                })
                print(f"  📄 #{processed_count} [{lang} | {page_count} sf.] {file} ({author})")

            elif ext == '.zip':
                try:
                    with zipfile.ZipFile(full_path, 'r') as z:
                        for zinfo in z.infolist():
                            if not zinfo.is_dir():
                                z_ext = os.path.splitext(zinfo.filename)[1].lower()
                                if z_ext == '.pdf':
                                    processed_count += 1
                                    filename = os.path.basename(zinfo.filename)
                                    try:
                                        data = z.read(zinfo.filename)
                                        page_count, preview = parse_pdf_bytes(data)
                                    except Exception as e:
                                        page_count, preview = 1, f"Arşiv okuma hatası: {e}"

                                    lang = detect_language(preview, zinfo.filename)
                                    author = detect_author(filename, os.path.dirname(zinfo.filename), preview)
                                    clean_preview = preview[:250].strip() or "(Görsel veya Özel Sayfa İçeriği)"

                                    results.append({
                                        "Kitap Adı": filename,
                                        "Yazar": author,
                                        "Dil": lang,
                                        "Sayfa Sayısı": page_count,
                                        "1.-3. Sayfa Özeti": clean_preview,
                                        "Format": "PDF (ZIP)",
                                        "Tam Dosya Yolu": f"{full_path} -> {zinfo.filename}"
                                    })
                                    if processed_count % 50 == 0 or processed_count <= 10:
                                        print(f"  📦 #{processed_count} [{lang} | {page_count} sf.] {filename} ({author})")
                except Exception as e:
                    print(f"⚠️ ZIP okuma hatası ({file}): {e}")

    elapsed = time.time() - start_time

    # Sort results by Language then Author then Title
    results.sort(key=lambda x: (x['Dil'], x['Yazar'], x['Kitap Adı'].lower()))

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['Kitap Adı', 'Yazar', 'Dil', 'Sayfa Sayısı', '1.-3. Sayfa Özeti', 'Format', 'Tam Dosya Yolu']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 75)
    print("✅ ANALİZ TAMAMLANDI VE İŞLENDİ!")
    print(f"📚 Toplam Analiz Edilen Kitap Sayısı : {len(results)}")
    print(f"⏱️ Geçen Süre                           : {elapsed:.2f} saniye")
    print(f"💾 Oluşturulan CSV Dosyası              : {csv_path}")
    print("=" * 75)

if __name__ == "__main__":
    analyze_all_books()
