import os
import csv
import re

def merge_converted_pdfs(converted_dir=r"C:\Users\default.LAPTOP-OBA1HVU9\.antigravity-ide\Converted_PDFs",
                        csv_main="kitaplar_listesi.csv",
                        csv_by_author="kitaplar_yazarlarina_gore.csv"):
    """
    Sonradan PDF'e dönüştürülen 104 adet yeni kitabı ana PDF kitap koleksiyonuna
    ve yazar listelerine otomatik olarak ekler ve günceller.
    """
    csv_main_abs = os.path.abspath(csv_main)
    csv_by_author_abs = os.path.abspath(csv_by_author)
    converted_dir_abs = os.path.abspath(converted_dir)

    print("=" * 75)
    print("🔗 DÖNÜŞTÜRÜLEN PDF'LER ANA KİTAP KOLEKSİYONUNA EKLENİYOR")
    print(f"📂 Dönüştürülen PDF Klasörü: {converted_dir_abs}")
    print(f"📄 Ana Kitap Listesi       : {csv_main_abs}")
    print("=" * 75 + "\n")

    # Mevcut kitap listesini oku
    all_books = []
    with open(csv_main_abs, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_books.append(row)

    initial_count = len(all_books)

    # Dönüştürülen yeni PDF dosyalarını ekle
    added_count = 0
    if os.path.exists(converted_dir_abs):
        for f in os.listdir(converted_dir_abs):
            if f.lower().endswith('.pdf') and f != 'temp.pdf':
                full_path = os.path.join(converted_dir_abs, f)
                try:
                    size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2)
                except Exception:
                    size_mb = 0.0

                all_books.append({
                    'Kitap Adı': f,
                    'Dosya Tipi': 'PDF (Dönüştürüldü)',
                    'Kaynak / Durum': 'Dönüştürülmüş PDF',
                    'Tam Dosya Yolu': full_path,
                    'Bulunduğu Klasör': converted_dir_abs,
                    'Boyut (MB)': str(size_mb)
                })
                added_count += 1

    # Ana Kitap CSV Listesini Güncelle
    with open(csv_main_abs, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['Kitap Adı', 'Dosya Tipi', 'Kaynak / Durum', 'Tam Dosya Yolu', 'Bulunduğu Klasör', 'Boyut (MB)']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_books)

    # Yazarlara Göre Güncel Liste Oluştur
    by_author_rows = []
    for b in all_books:
        auth = detect_author(b['Kitap Adı'], b['Bulunduğu Klasör'], b['Tam Dosya Yolu'])
        by_author_rows.append({
            'Yazar': auth,
            'Kitap Adı': b['Kitap Adı'],
            'Format': b['Dosya Tipi'],
            'Kaynak / Durum': b['Kaynak / Durum'],
            'Bulunduğu Klasör': b['Bulunduğu Klasör'],
            'Tam Dosya Yolu': b['Tam Dosya Yolu'],
            'Boyut (MB)': b['Boyut (MB)']
        })

    by_author_rows.sort(key=lambda x: (x['Yazar'], x['Kitap Adı'].lower()))

    with open(csv_by_author_abs, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['Yazar', 'Kitap Adı', 'Format', 'Kaynak / Durum', 'Bulunduğu Klasör', 'Tam Dosya Yolu', 'Boyut (MB)']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(by_author_rows)

    print("=" * 75)
    print("✅ GÜNCELLEME TAMAMLANDI!")
    print(f"📊 Önceki Kitap Sayısı            : {initial_count}")
    print(f"➕ Eklenen Yeni Dönüştürülmüş PDF : {added_count}")
    print(f"📚 Güncel Toplam PDF Kitap Sayısı : {len(all_books)}")
    print(f"💾 Güncellenen CSV Dosyası        : {csv_main_abs}")
    print("=" * 75)

def detect_author(filename, folder, full_path):
    path = (folder + '/' + filename).replace('\\', '/')
    name = filename.strip()
    name_lower = name.lower()

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
    if 'George Orwell' in name or '1984' in name:
        return 'George Orwell'
    if 'Tolstoy' in name or 'Savaş ve Barış' in name:
        return 'Tolstoy'
    if 'Charles Dickens' in name:
        return 'Charles Dickens'
    if 'Sun Tzu' in name or 'Art of War' in name:
        return 'Sun Tzu'
    if 'İlber Ortaylı' in name or 'Ortaylı' in name:
        return 'İlber Ortaylı'
    if 'Hanefi Avcı' in name:
        return 'Hanefi Avcı'
    if 'Mark Manson' in name:
        return 'Mark Manson'
    if 'David Burns' in name:
        return 'David Burns'

    match = re.match(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)+)\s*-\s*', name)
    if match:
        cand = match.group(1).strip()
        if len(cand) > 4 and cand not in ['Mesnevi Hikayelerinden', 'Final sample', 'Lab and', 'Kuresel Dunyada', 'Untitled document']:
            return cand

    return 'Çeşitli / Belirtilmemiş'

if __name__ == "__main__":
    merge_converted_pdfs()
