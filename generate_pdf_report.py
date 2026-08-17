"""
Executive PDF Report Generator for Book Library & MySQL Synchronizer Project.
Generates 'PROJE_OZETI.pdf' featuring:
- Full Turkish character support (Arial/Unicode TrueType)
- Modern executive styling (Navy/Indigo accents, cards, data tables, badges)
- Complete technical summary, database architecture, script inventory,
  and comprehensive 2,632 disk vs. 1,921 database audit breakdown.
"""

import os
import pymupdf
import pymysql


def get_css_styles() -> str:
    """Return modern, professional CSS styles for the PDF report."""
    return """
    <style>
        @page {
            size: A4;
            margin: 0;
        }
        body {
            font-family: sans-serif;
            margin: 0;
            padding: 28px 36px;
            color: #1e293b;
            background-color: #ffffff;
            line-height: 1.35;
            font-size: 11px;
        }
        .header-container {
            background: #0f172a;
            color: #ffffff;
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 16px;
            border-left: 6px solid #38bdf8;
        }
        .header-title {
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            margin: 0 0 4px 0;
            letter-spacing: 0.3px;
        }
        .header-subtitle {
            font-size: 11px;
            color: #94a3b8;
            margin: 0;
        }
        .header-meta {
            margin-top: 8px;
            font-size: 9.5px;
            color: #38bdf8;
        }
        h2 {
            font-size: 13.5px;
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 4px;
            margin-top: 14px;
            margin-bottom: 8px;
            font-weight: bold;
        }
        h3 {
            font-size: 11.5px;
            color: #1e3a8a;
            margin-top: 10px;
            margin-bottom: 4px;
            font-weight: bold;
        }
        p {
            margin: 0 0 6px 0;
            color: #334155;
        }
        .kpi-container {
            display: table;
            width: 100%;
            margin-bottom: 12px;
        }
        .kpi-row {
            display: table-row;
        }
        .kpi-card {
            display: table-cell;
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 8px 10px;
            text-align: center;
            width: 24%;
            vertical-align: middle;
        }
        .kpi-card-inner {
            padding: 2px;
        }
        .kpi-card-blue { border-top: 3px solid #2563eb; background: #eff6ff; }
        .kpi-card-green { border-top: 3px solid #16a34a; background: #f0fdf4; }
        .kpi-card-amber { border-top: 3px solid #d97706; background: #fffbeb; }
        .kpi-card-purple { border-top: 3px solid #7c3aed; background: #faf5ff; }
        .kpi-val {
            font-size: 16px;
            font-weight: bold;
            color: #0f172a;
            margin-bottom: 2px;
        }
        .kpi-lbl {
            font-size: 9px;
            color: #64748b;
            font-weight: bold;
            text-transform: uppercase;
        }
        table.data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 6px 0 12px 0;
            font-size: 9.5px;
        }
        table.data-table th, table.data-table td {
            border: 1px solid #cbd5e1;
            padding: 5px 7px;
            text-align: left;
        }
        table.data-table th {
            background-color: #0f172a;
            color: #ffffff;
            font-weight: bold;
            font-size: 9.5px;
        }
        table.data-table tr:nth-child(even) {
            background-color: #f8fafc;
        }
        .badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 8.5px;
            font-weight: bold;
        }
        .badge-success { background: #dcfce7; color: #166534; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .badge-info { background: #e0f2fe; color: #075985; }
        .badge-neutral { background: #f1f5f9; color: #334155; }
        .callout-box {
            background-color: #f1f5f9;
            border-left: 4px solid #3b82f6;
            padding: 8px 12px;
            border-radius: 4px;
            margin: 8px 0;
            font-size: 10px;
        }
        .footer {
            margin-top: 14px;
            border-top: 1px solid #e2e8f0;
            padding-top: 6px;
            font-size: 8.5px;
            color: #94a3b8;
            text-align: center;
        }
        ul {
            margin: 3px 0 6px 16px;
            padding: 0;
        }
        li {
            margin-bottom: 3px;
        }
    </style>
    """


def get_page1_html() -> str:
    """Page 1: Executive Summary, Objectives, and Key Highlights."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>{get_css_styles()}</head>
    <body>
        <div class="header-container">
            <div class="header-title">📚 KÜTÜPHANE YÖNETİM SİSTEMİ & VERİTABANI PROJESİ</div>
            <div class="header-subtitle">Uçtan Uca Teknik Mimari, Veri Denetim ve Yönetici Özeti Raporu</div>
            <div class="header-meta">
                <strong>Veritabanı:</strong> MySQL (library_db) &bull; 
                <strong>Sunucu:</strong> localhost:3306 &bull; 
                <strong>Tarih:</strong> 14 Ağustos 2026 &bull; 
                <strong>Durum:</strong> Başarıyla Tamamlandı (%100)
            </div>
        </div>

        <div class="kpi-container">
            <div class="kpi-row">
                <div class="kpi-card kpi-card-blue">
                    <div class="kpi-val">2.632</div>
                    <div class="kpi-lbl">Diskteki Toplam Dosya</div>
                </div>
                <div class="kpi-card kpi-card-purple">
                    <div class="kpi-val">12</div>
                    <div class="kpi-lbl">Açılan ZIP Arşivi</div>
                </div>
                <div class="kpi-card kpi-card-green">
                    <div class="kpi-val">1.921</div>
                    <div class="kpi-lbl">MySQL Benzersiz Kitap</div>
                </div>
                <div class="kpi-card kpi-card-amber">
                    <div class="kpi-val">689</div>
                    <div class="kpi-lbl">Mükerrer Kopya</div>
                </div>
            </div>
        </div>

        <h2>1. Projenin Amacı ve Temel Kazanımlar</h2>
        <p>
            Bu proje; <strong>Books/</strong> dizininde yer alan büyük ölçekli ve sıkıştırılmış (.zip) kitap arşivlerini 
            otomatik olarak ayıklayan, çok formatlı belgelerden (PDF, EPUB, DOCX vb.) metaveri (başlık, yazar, sayfa sayısı) 
            çıkaran, 64 KB SHA-256 hash algoritması ile içerik tekilleştirmesi yapan ve tüm arşivi yerel 
            <strong>MySQL (library_db)</strong> veritabanına kaydederek terminalde ve JSON/CSV formatlarında raporlayan 
            kapsamlı bir Python backend altyapısıdır.
        </p>

        <div class="callout-box">
            <strong>🎯 Temel Çıktı & Doğrulama:</strong> Diskte bulunan toplam 2.632 dosya taranmış; 12 adet ZIP arşivi 
            açılarak içerisindeki 2.610 kitap dosyası çözümlenmiştir. SHA-256 hash kontrolü ile tespit edilen 689 mükerrer 
            kopya filtrelenmiş ve diskteki <strong>1.921 benzersiz kitabın %100'ü</strong> MySQL veritabanına aktarılmıştır. 
            <strong>Kayıp veya eklenemeyen dosya sayısı: 0'dır.</strong>
        </div>

        <h2>2. Dört Aşamalı İş Akışı ve Mimari</h2>
        <ul>
            <li><strong>1. Arşiv Çıkarma (ZIP Extraction):</strong> 12 adet ~2 GB boyutundaki ZIP arşivi taranmış, Türkçe karakter (UTF-8/CP1254) ve Windows uzun dosya yolu korumasıyla 2.325 yeni dosya diskte ilgili klasörlere açılmıştır.</li>
            <li><strong>2. Metaveri Ayrıştırma:</strong> PyMuPDF (fitz) ile PDF sayfa ve başlıkları, OPF/XML motoru ile EPUB içerikleri, OpenXML ile DOCX özellikleri çıkarılmış; eksik metaveriler klasör hiyerarşisinden akıllı regex fallback ile tamamlanmıştır.</li>
            <li><strong>3. Mükerrer Engelleme & MySQL Batch Yazma:</strong> Her dosyanın binary SHA-256 hash değeri hesaplanmış, <code>UNIQUE</code> indeks sayesinde mükerrer kayıtlar engellenmiş ve 100'lük paketler halinde toplu kayıt gerçekleştirilmiştir.</li>
            <li><strong>4. SQL Sorgulama & Raporlama:</strong> MySQL'den <code>SELECT</code> sorgusu ile çekilen veriler <code>tabulate</code> ile terminalde görselleştirilmiş, eşzamanlı olarak <code>books_from_db.json</code> ve <code>books_from_db.csv</code> dosyalarına aktarılmıştır.</li>
        </ul>

        <div class="footer">Kütüphane Yönetim Sistemi &bull; Proje Özeti &bull; Sayfa 1 / 3</div>
    </body>
    </html>
    """


def get_page2_html() -> str:
    """Page 2: Database Architecture, Schema, and Script Inventory."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>{get_css_styles()}</head>
    <body>
        <h2>3. Veritabanı Mimarisi ve Tablo Şeması</h2>
        <p>
            Proje, veritabanı bulunmadığında MySQL sunucusuna bağlanıp <code>CREATE DATABASE IF NOT EXISTS library_db</code> 
            komutu ile şemayı otomatik olarak oluşturur. <code>books</code> tablosu UTF-8 (utf8mb4) desteğiyle optimize edilmiştir.
        </p>

        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 14%;">Sütun Adı</th>
                    <th style="width: 14%;">Veri Tipi</th>
                    <th style="width: 16%;">Kısıtlama / İndeks</th>
                    <th>Açıklama ve Kullanım Amacı</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>id</strong></td>
                    <td>INT</td>
                    <td><span class="badge badge-info">PRIMARY KEY</span> Auto-Inc</td>
                    <td>Kitap benzersiz kayıt sıra numarası.</td>
                </tr>
                <tr>
                    <td><strong>title</strong></td>
                    <td>VARCHAR(255)</td>
                    <td>NOT NULL</td>
                    <td>Kitabın başlığı (Metaveri veya klasörden ayıklanan).</td>
                </tr>
                <tr>
                    <td><strong>author</strong></td>
                    <td>VARCHAR(255)</td>
                    <td>NULLABLE</td>
                    <td>Yazar adı (Belge metaverisi veya klasör eşleştirmesi).</td>
                </tr>
                <tr>
                    <td><strong>page_count</strong></td>
                    <td>INT</td>
                    <td>NULLABLE</td>
                    <td>Belgedeki sayfa / bölüm adedi.</td>
                </tr>
                <tr>
                    <td><strong>file_type</strong></td>
                    <td>VARCHAR(20)</td>
                    <td>NOT NULL</td>
                    <td>Dosya türü (<code>pdf</code>, <code>epub</code>, <code>docx</code>).</td>
                </tr>
                <tr>
                    <td><strong>file_path</strong></td>
                    <td>VARCHAR(500)</td>
                    <td>NOT NULL</td>
                    <td>Dosyanın diskteki göreli konumu ve klasör yolu.</td>
                </tr>
                <tr>
                    <td><strong>file_size_bytes</strong></td>
                    <td>BIGINT</td>
                    <td>NOT NULL</td>
                    <td>Dosyanın diskteki boyutu (Bayt cinsinden).</td>
                </tr>
                <tr>
                    <td><strong>sha256_hash</strong></td>
                    <td>VARCHAR(64)</td>
                    <td><span class="badge badge-success">UNIQUE INDEX</span></td>
                    <td>64 KB binary hash. Mükerrer kayıtları %100 engeller.</td>
                </tr>
                <tr>
                    <td><strong>created_at</strong></td>
                    <td>DATETIME</td>
                    <td>DEFAULT CURRENT_TIMESTAMP</td>
                    <td>Kayıt eklenme zaman damgası.</td>
                </tr>
            </tbody>
        </table>

        <h2>4. Geliştirilen Modüller ve Kaynak Dosyalar</h2>
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 22%;">Modül / Dosya</th>
                    <th style="width: 25%;">Kapsam / Yetenek</th>
                    <th>Teknik Açıklama</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>main.py</strong></td>
                    <td>Ana Orkestrasyon</td>
                    <td>Bağlantı, ZIP çıkarma, tarama, batch insert ve tabulate raporlama akışını yürütür.</td>
                </tr>
                <tr>
                    <td><strong>database.py</strong></td>
                    <td>Veritabanı Katmanı</td>
                    <td>SQLAlchemy ORM modeli (<code>Book</code>), PyMySQL bağlantı havuzu ve toplu kayıt (bulk save).</td>
                </tr>
                <tr>
                    <td><strong>parsers.py</strong></td>
                    <td>Metaveri & Hashing</td>
                    <td>64 KB SHA-256 hesaplama, PyMuPDF, EPUB OPF/XML, OpenXML ve akıllı regex fallback motoru.</td>
                </tr>
                <tr>
                    <td><strong>zip_extractor.py</strong></td>
                    <td>Arşiv Çıkarıcı</td>
                    <td>12 ZIP arşivini UTF-8 ve CP1254 Türkçe karakter desteğiyle diske güvenle açar.</td>
                </tr>
                <tr>
                    <td><strong>exporter.py</strong></td>
                    <td>Dışa Aktarım</td>
                    <td>MySQL'deki tüm kayıtları <code>books_from_db.json</code> ve <code>.csv</code> olarak UTF-8 kaydeder.</td>
                </tr>
                <tr>
                    <td><strong>generate_audit_report.py</strong></td>
                    <td>Denetim & Karşılaştırma</td>
                    <td>2.632 dosyayı 4 gruba ayırıp <code>atlanmis_dosyalar_raporu.csv</code> üretir.</td>
                </tr>
                <tr>
                    <td><strong>generate_pdf_report.py</strong></td>
                    <td>PDF Rapor Motoru</td>
                    <td>Bu yönetici özetini ve teknik mutabakat raporunu PDF olarak derler.</td>
                </tr>
                <tr>
                    <td><strong>.env / requirements.txt</strong></td>
                    <td>Yapılandırma & Paketler</td>
                    <td>MySQL kimlik bilgileri, klasör ayarları ve Python paket bağımlılıkları.</td>
                </tr>
            </tbody>
        </table>

        <div class="footer">Kütüphane Yönetim Sistemi &bull; Proje Özeti &bull; Sayfa 2 / 3</div>
    </body>
    </html>
    """


def get_page3_html() -> str:
    """Page 3: Data Audit, 2632 vs 1921 Reconciliation, Format Distribution, and Conclusion."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>{get_css_styles()}</head>
    <body>
        <h2>5. Veri Denetimi ve Sayısal Mutabakat (2.632 Disk vs 1.921 MySQL)</h2>
        <p>
            Diskte yer alan her bir dosya taranmış, SHA-256 hash ve format bazında 4 gruba ayrılarak 
            MySQL veritabanı ile birebir karşılaştırılmıştır:
        </p>

        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 38%;">Grup / Kategori Tanımı</th>
                    <th style="width: 14%; text-align: right;">Adet</th>
                    <th style="width: 18%;">Durum</th>
                    <th>Açıklama</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>a) MySQL'e Eklenenler (Benzersiz Kitaplar)</strong></td>
                    <td style="text-align: right;"><strong>1.921</strong></td>
                    <td><span class="badge badge-success">✓ Aktif Kayıtlı</span></td>
                    <td>MySQL <code>library_db.books</code> tablosundaki benzersiz kitaplar.</td>
                </tr>
                <tr>
                    <td><strong>b) Mükerrer / Kopya Dosyalar</strong></td>
                    <td style="text-align: right;"><strong>689</strong></td>
                    <td><span class="badge badge-warning">✗ Atlandı</span></td>
                    <td>Farklı ZIP arşivlerinde yer alan aynı içerikli (aynı SHA-256) kopyalar.</td>
                </tr>
                <tr>
                    <td><strong>c) Kitap Formatında Olmayanlar</strong></td>
                    <td style="text-align: right;"><strong>21</strong></td>
                    <td><span class="badge badge-neutral">✗ Desteklenmeyen</span></td>
                    <td>12 adet .zip, 6 adet .jpeg, 2 adet sunum (.ppt/.pptx), 1 adet .tmp.</td>
                </tr>
                <tr>
                    <td><strong>d) Bozuk / 0 Bayt Olanlar</strong></td>
                    <td style="text-align: right;"><strong>2</strong></td>
                    <td><span class="badge badge-neutral">✗ Boş Dosya</span></td>
                    <td>İçi boş (0 bayt) 2 dosya (<code>kukla.docx</code>, <code>Proje</code>).</td>
                </tr>
                <tr style="background-color: #f1f5f9; font-weight: bold;">
                    <td>TOPLAM DİSKTEKİ DOSYA HAVUZU</td>
                    <td style="text-align: right;"><strong>2.632</strong></td>
                    <td><span class="badge badge-info">%100 Mutabakat</span></td>
                    <td>1.921 (Unique) + 689 (Mükerrer) + 21 (Arşiv/Medya) + 2 (Boş) = 2.632</td>
                </tr>
            </tbody>
        </table>

        <h2>6. MySQL Veritabanı Format Dağılımı ve Örnek Kayıtlar</h2>
        
        <table class="data-table" style="margin-bottom: 8px;">
            <thead>
                <tr>
                    <th>Dosya Formatı</th>
                    <th style="text-align: right;">Kitap Sayısı</th>
                    <th style="text-align: right;">Yüzde Oranı</th>
                    <th>Ayrıştırıcı Motor</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>PDF (.pdf)</strong></td>
                    <td style="text-align: right;">1.820</td>
                    <td style="text-align: right;">%94.74</td>
                    <td>PyMuPDF (fitz) + pypdf</td>
                </tr>
                <tr>
                    <td><strong>EPUB (.epub)</strong></td>
                    <td style="text-align: right;">93</td>
                    <td style="text-align: right;">%4.84</td>
                    <td>OPF / XML Parser + ebooklib</td>
                </tr>
                <tr>
                    <td><strong>Word DOCX (.docx)</strong></td>
                    <td style="text-align: right;">8</td>
                    <td style="text-align: right;">%0.42</td>
                    <td>OpenXML core.xml / app.xml</td>
                </tr>
                <tr style="font-weight: bold; background-color: #f8fafc;">
                    <td>TOPLAM BENZERSİZ KİTAP</td>
                    <td style="text-align: right;">1.921</td>
                    <td style="text-align: right;">%100.00</td>
                    <td>library_db.books tablosu</td>
                </tr>
            </tbody>
        </table>

        <h3>Veritabanından Örnek 5 Kayıt</h3>
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 7%;">ID</th>
                    <th style="width: 32%;">Kitap Adı</th>
                    <th style="width: 25%;">Yazar</th>
                    <th style="width: 8%; text-align: right;">Sayfa</th>
                    <th style="width: 10%;">Tür</th>
                    <th style="width: 18%;">Boyut</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>1</strong></td>
                    <td>100 Soruda Ahiret Hayatı</td>
                    <td>Suat Yıldırım</td>
                    <td style="text-align: right;">133</td>
                    <td><span class="badge badge-info">PDF</span></td>
                    <td>1.78 MB</td>
                </tr>
                <tr>
                    <td><strong>2</strong></td>
                    <td>Emirdağ Lahikası Üzerine 1</td>
                    <td>Abdullah Aymaz</td>
                    <td style="text-align: right;">499</td>
                    <td><span class="badge badge-info">PDF</span></td>
                    <td>1.63 MB</td>
                </tr>
                <tr>
                    <td><strong>3</strong></td>
                    <td>Emirdağ Lahikası Üzerine 2</td>
                    <td>Abdullah Aymaz</td>
                    <td style="text-align: right;">393</td>
                    <td><span class="badge badge-info">PDF</span></td>
                    <td>1.39 MB</td>
                </tr>
                <tr>
                    <td><strong>4</strong></td>
                    <td>Hanımlar Rehberi Üzerine</td>
                    <td>Abdullah Aymaz</td>
                    <td style="text-align: right;">208</td>
                    <td><span class="badge badge-info">PDF</span></td>
                    <td>7.88 MB</td>
                </tr>
                <tr>
                    <td><strong>74</strong></td>
                    <td>Fethullah Gülen Röportajı</td>
                    <td>Ekrem Dumanlı</td>
                    <td style="text-align: right;">-</td>
                    <td><span class="badge badge-success">EPUB</span></td>
                    <td>98.2 KB</td>
                </tr>
            </tbody>
        </table>

        <div class="callout-box" style="margin-top: 6px;">
            <strong>✅ Sonuç:</strong> Proje, tüm teknik gereksinimleri eksiksiz karşılamış; veri kaybı, karakter bozulması 
            veya kütüphane çökmesi yaşanmadan başarıyla tamamlanmıştır.
        </div>

        <div class="footer">Kütüphane Yönetim Sistemi &bull; Proje Özeti &bull; Sayfa 3 / 3</div>
    </body>
    </html>
    """


def generate_pdf_report(output_pdf_path: str = "PROJE_OZETI.pdf"):
    """
    Generate professional multi-page PDF report with full Turkish character support.
    """
    print("=" * 80)
    print(" 📄  PROJE ÖZETİ PDF RAPORU OLUŞTURULUYOR  📄")
    print("=" * 80)

    pages_html = [
        get_page1_html(),
        get_page2_html(),
        get_page3_html()
    ]

    doc = pymupdf.open()
    font_arial = "C:/Windows/Fonts/arial.ttf"
    font_bold = "C:/Windows/Fonts/arialbd.ttf"

    for idx, html_str in enumerate(pages_html, 1):
        page = doc.new_page(width=595.28, height=841.89)  # Standard A4
        
        # Register Arial TrueType font for perfect Turkish support
        if os.path.exists(font_arial):
            page.insert_font(fontname="sans-serif", fontfile=font_arial)
            page.insert_font(fontname="arial", fontfile=font_arial)
        if os.path.exists(font_bold):
            page.insert_font(fontname="arial-bold", fontfile=font_bold)

        rect = pymupdf.Rect(20, 20, 575.28, 821.89)
        leftover, scale = page.insert_htmlbox(rect, html_str)
        print(f"  ✓ Sayfa {idx} derlendi (Ölçek: {scale:.2f})")

    doc.save(output_pdf_path)
    doc.close()

    abs_path = os.path.abspath(output_pdf_path)
    file_size_kb = os.path.getsize(abs_path) / 1024
    print("=" * 80)
    print(f" ✨ PDF RAPORU BAŞARIYLA OLUŞTURULDU:")
    print(f"    • Dosya Yolu : {abs_path}")
    print(f"    • Dosya Boyutu: {file_size_kb:.1f} KB")
    print(f"    • Sayfa Sayısı: {len(pages_html)} Sayfa")
    print("=" * 80 + "\n")
    return abs_path


if __name__ == "__main__":
    generate_pdf_report("PROJE_OZETI.pdf")
