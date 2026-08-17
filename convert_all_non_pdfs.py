import os
import re
import zipfile
import xml.etree.ElementTree as ET

def tr_to_ascii(text):
    """Converts Turkish characters to standard Latin-1 compatible characters for standard PDF fonts."""
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

def create_pdf_from_text(pdf_filename, text_content, title=""):
    """Generates a valid PDF document from raw text content using pure Python."""
    output_dir = os.path.dirname(pdf_filename)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    text_content = tr_to_ascii(text_content)
    lines = []

    if title:
        lines.append(f"=== {title.upper()} ===")
        lines.append("")

    for raw_line in text_content.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        while len(line) > 85:
            lines.append(line[:85])
            line = line[85:]
        if line:
            lines.append(line)

    pages_lines = []
    current_page = []
    for line in lines:
        current_page.append(line)
        if len(current_page) >= 50:
            pages_lines.append(current_page)
            current_page = []
    if current_page:
        pages_lines.append(current_page)

    if not pages_lines:
        pages_lines = [["(İçerik Bulunamadı / Content Empty)"]]

    objects = []
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")

    page_obj_ids = [str(3 + i * 2) for i in range(len(pages_lines))]
    kids_str = " ".join([f"{pid} 0 R" for pid in page_obj_ids])
    objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(pages_lines)} >>\nendobj")

    obj_id = 3
    for page_num, p_lines in enumerate(pages_lines, start=1):
        content_id = obj_id + 1
        page_obj = (
            f"{obj_id} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> >> >> "
            f"/MediaBox [0 0 595 842] /Contents {content_id} 0 R >>\nendobj"
        )
        objects.append(page_obj)

        stream_cmds = ["BT", "/F1 10 Tf", "13 TL", "40 800 TD"]
        for l in p_lines:
            clean_l = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            safe_l = clean_l.encode("latin1", "replace").decode("latin1")
            stream_cmds.append(f"({safe_l}) T*")
        stream_cmds.append("ET")

        stream_data = "\n".join(stream_cmds)
        content_obj = f"{content_id} 0 obj\n<< /Length {len(stream_data)} >>\nstream\n{stream_data}\nendstream\nendobj"
        objects.append(content_obj)
        obj_id += 2

    with open(pdf_filename, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for obj in objects:
            offsets.append(f.tell())
            f.write(obj.encode("latin1") + b"\n")

        xref_offset = f.tell()
        f.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets:
            f.write(f"{off:010d} 00000 n \n".encode("latin1"))

        trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
        f.write(trailer.encode("latin1"))

def extract_epub_text(epub_path):
    text_chunks = []
    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            for item in z.infolist():
                if item.filename.endswith(('.html', '.xhtml', '.htm')):
                    html_bytes = z.read(item.filename)
                    html_str = html_bytes.decode('utf-8', errors='ignore')
                    clean_text = re.sub(r'<[^>]+>', ' ', html_str)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if clean_text:
                        text_chunks.append(clean_text)
    except Exception as e:
        text_chunks.append(f"Hata: EPUB okunamadı ({e})")
    return "\n\n".join(text_chunks)

def extract_docx_text(docx_path):
    text_chunks = []
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            if 'word/document.xml' in z.namelist():
                xml_bytes = z.read('word/document.xml')
                tree = ET.fromstring(xml_bytes)
                for elem in tree.iter():
                    if elem.tag.endswith('t') and elem.text:
                        text_chunks.append(elem.text)
    except Exception as e:
        text_chunks.append(f"Hata: DOCX okunamadı ({e})")
    return " ".join(text_chunks)

def convert_all_non_pdfs(target_books_dir=r"C:\Users\default.LAPTOP-OBA1HVU9\.antigravity-ide\Books",
                         output_dir=r"C:\Users\default.LAPTOP-OBA1HVU9\.antigravity-ide\Converted_PDFs"):
    os.makedirs(output_dir, exist_ok=True)
    supported_non_pdf_exts = {'.epub', '.mobi', '.txt', '.doc', '.docx', '.ppt', '.pptx', '.html'}

    converted_count = 0

    print("=" * 65)
    print("🔄 PDF OLMAYAN KİTAPLARI PDF'E DÖNÜŞTÜRME BAŞLATILDI")
    print(f"📁 Taranan Klasör : {target_books_dir}")
    print(f"📂 Hedef PDF Yolu: {output_dir}")
    print("=" * 65 + "\n")

    for root, dirs, files in os.walk(target_books_dir):
        for f in files:
            full_path = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()

            if ext in supported_non_pdf_exts:
                pdf_name = os.path.splitext(f)[0] + ".pdf"
                dest_pdf_path = os.path.join(output_dir, pdf_name)

                if ext == '.epub':
                    text = extract_epub_text(full_path)
                elif ext == '.docx':
                    text = extract_docx_text(full_path)
                else:
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as tf:
                            text = tf.read()
                    except Exception:
                        text = f"{f} içeriği okundu."

                create_pdf_from_text(dest_pdf_path, text, title=os.path.splitext(f)[0])
                converted_count += 1
                print(f"  ✅ Dönüştürüldü #{converted_count}: {f} -> {pdf_name}")

            elif ext == '.zip':
                try:
                    with zipfile.ZipFile(full_path, 'r') as z:
                        for zinfo in z.infolist():
                            if not zinfo.is_dir():
                                z_ext = os.path.splitext(zinfo.filename)[1].lower()
                                if z_ext in supported_non_pdf_exts:
                                    base_filename = os.path.basename(zinfo.filename)
                                    if not base_filename:
                                        continue
                                    pdf_name = os.path.splitext(base_filename)[0] + ".pdf"
                                    dest_pdf_path = os.path.join(output_dir, pdf_name)

                                    file_bytes = z.read(zinfo.filename)
                                    if z_ext == '.epub':
                                        temp_epub = os.path.join(output_dir, "temp.epub")
                                        with open(temp_epub, "wb") as tmp:
                                            tmp.write(file_bytes)
                                        text = extract_epub_text(temp_epub)
                                        if os.path.exists(temp_epub):
                                            os.remove(temp_epub)
                                    elif z_ext == '.docx':
                                        temp_docx = os.path.join(output_dir, "temp.docx")
                                        with open(temp_docx, "wb") as tmp:
                                            tmp.write(file_bytes)
                                        text = extract_docx_text(temp_docx)
                                        if os.path.exists(temp_docx):
                                            os.remove(temp_docx)
                                    else:
                                        text = file_bytes.decode('utf-8', errors='ignore')

                                    create_pdf_from_text(dest_pdf_path, text, title=os.path.splitext(base_filename)[0])
                                    converted_count += 1
                                    print(f"  📦 Arşivden Dönüştürüldü #{converted_count}: {base_filename} -> {pdf_name}")
                except Exception as e:
                    print(f"⚠️ ZIP okuma hatası ({f}): {e}")

    print("\n" + "=" * 65)
    print("🎉 DÖNÜŞTÜRME İŞLEMİ TAMAMLANDI!")
    print(f"📄 Toplam PDF'e Dönüştürülen Dosya : {converted_count}")
    print(f"📁 PDF Dosyalarının Klasörü       : {output_dir}")
    print("=" * 65)

if __name__ == "__main__":
    convert_all_non_pdfs()
