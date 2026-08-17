# 💎 DiamondLibrary

> **Yüksek Hızlı Dijital Kütüphane & Tam Metin Arama Platformu**
> 1.913 Kitap &bull; 429.308 Sayfa &bull; ~120 Milyon Kelime &bull; SQLite FTS5 Motoru &bull; REST API

---

## 📌 Proje Hakkında

**DiamondLibrary**, çok formatlı (PDF, EPUB) dijital kitap arşivlerini otomatik olarak ayrıştıran, sayfa bazında metin indekslemesi (Inverted Index) yapan ve **15–30 milisaniye** içinde 120 milyon kelimelik külliyatta tam metin arama imkanı sunan modern bir arama motoru ve okuma platformudur.

---

## 🚀 Hızlı Başlangıç

### 1. Arama Sunucusunu Başlatma
```bash
python server.py
```
Sunucu başladığında tarayıcınızdan **[http://localhost:8000](http://localhost:8000)** adresine gidin.

### 2. Yeniden İndeksleme (Gerektiğinde)
```bash
python index_search.py
```

### 3. PDF / EPUB Metin Dönüştürme
```bash
python convert_to_txt.py
```

---

## 🛠️ Sistem Mimarisi & Yetenekler

- **Arama Motoru**: SQLite FTS5 (`unicode61` Türkçe Tokenizer + BM25 Alaka Sıralaması)
- **Backend**: Python Thread-Safe Çok İş Parçacıklı HTTP REST API
- **Frontend**: Glassmorphism, Google Fonts (`Outfit`, `Inter`), Koyu / Açık / Sepia Temaları
- **Dahili Okuyucu (In-App Reader)**: Arama sonucundaki sayfayı anında açar, aranan kelimeleri sayfa içinde parlatır, sayfa geçişleri ve font ayarlamaları sunar.

---

## 📄 REST API Uç Noktaları

| Endpoint | Yöntem | Açıklama |
|---|:---:|---|
| `/api/stats` | `GET` | Toplam kitap, sayfa, kelime sayısı ve veritabanı boyutu |
| `/api/search?q={kelime}` | `GET` | Sayfa düzeyinde tam metin arama ve vurgulu alıntılar |
| `/api/books` | `GET` | Sayfalamalı kitap kataloğu |
| `/api/books/{id}/page/{num}` | `GET` | Kitabın belirli bir sayfasının tam metni |
| `/api/books/{id}/download` | `GET` | Kitabın UTF-8 TXT dosyasını indirme |

---

&copy; 2026 DiamondLibrary. Tüm hakları saklıdır.
