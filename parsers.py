"""
Metadata Extraction and Hashing Module for Various Book Formats.
Supports PDF, EPUB, Word (.docx/.doc), TXT, and intelligent fallback filename parsing.
"""

import os
import re
import hashlib
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup

# Optional PyMuPDF (pymupdf / fitz)
try:
    import pymupdf as fitz  # type: ignore
    HAS_PYMUPDF = True
except Exception:
    try:
        import fitz  # type: ignore
        HAS_PYMUPDF = True
    except Exception:
        HAS_PYMUPDF = False

# Optional pypdf
try:
    import pypdf  # type: ignore
    HAS_PYPDF = True
except Exception:
    HAS_PYPDF = False

# Optional python-docx
try:
    import docx  # type: ignore
    HAS_DOCX = True
except Exception:
    HAS_DOCX = False

# Optional ebooklib
try:
    import ebooklib  # type: ignore
    from ebooklib import epub  # type: ignore
    HAS_EBOOKLIB = True
except Exception:
    HAS_EBOOKLIB = False



# Generic placeholder titles and authors that indicate bad metadata
GENERIC_METADATA_VALUES = {
    "untitled", "title", "author", "microsoft word", "word", "document",
    "pdf document", "scan", "default", "isimsiz", "kitap", "bilinmiyor",
    "corel draw", "adobe indesign", "quarkxpress", "calibre", "libreoffice",
    "wps office", "export", "print", "none", "null", "nan"
}

# Known author mappings from common folder names and file substrings
KNOWN_AUTHORS_MAP = {
    "suat yıldırım": "Suat Yıldırım",
    "suat yildirim": "Suat Yıldırım",
    "ahmet kurucan": "Ahmet Kurucan",
    "fethullah gülen": "M. Fethullah Gülen",
    "fethullah gulen": "M. Fethullah Gülen",
    "mfg": "M. Fethullah Gülen",
    "prl": "M. Fethullah Gülen",
    "hekimoglu ismail": "Hekimoğlu İsmail",
    "hekimoğlu ismail": "Hekimoğlu İsmail",
    "necmeddin şahiner": "Necmeddin Şahiner",
    "necmettin sahiner": "Necmeddin Şahiner",
    "davut aydüz": "Davut Aydüz",
    "davut ayduz": "Davut Aydüz",
    "vehbe zuhayli": "Vehbe Zuhayli",
    "ali ünal": "Ali Ünal",
    "ali unal": "Ali Ünal",
    "aytunc altindal": "Aytunç Altındal",
    "aytunç altındal": "Aytunç Altındal",
    "reşit haylamaz": "Reşit Haylamaz",
    "resid haylamaz": "Reşit Haylamaz",
    "mehmet akar": "Mehmet Akar",
    "umberto eco": "Umberto Eco",
    "ibrahim canan": "İbrahim Canan",
    "ayhan tekines": "Ayhan Tekineş",
    "ayhan tekineş": "Ayhan Tekineş",
    "arif sarsılmaz": "Arif Sarsılmaz",
    "haris el muhasibi": "Haris El-Muhasibi",
    "haris-el-muhasibi": "Haris El-Muhasibi",
    "imam rabbani": "İmam-ı Rabbani",
    "imam-i-rabbani": "İmam-ı Rabbani"
}


def calculate_sha256(file_path: str, chunk_size: int = 64 * 1024) -> str:
    """
    Calculate the SHA-256 hash of a file by reading it in 64 KB binary chunks.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def clean_string(val: Optional[str]) -> str:
    """
    Clean whitespace, non-printable characters, and HTML tags from string values.
    """
    if not val:
        return ""
    
    # Strip HTML tags if any
    if "<" in val and ">" in val:
        try:
            val = BeautifulSoup(val, "html.parser").get_text()
        except Exception:
            pass

    # Normalize unicode spaces and control characters
    val = re.sub(r"[\r\n\t]+", " ", str(val))
    val = re.sub(r"\s+", " ", val).strip()
    return val


def is_valid_metadata_value(val: Optional[str]) -> bool:
    """
    Check if an extracted metadata value is genuine or a generic placeholder.
    """
    if not val:
        return False
    cleaned = clean_string(val).lower()
    if len(cleaned) < 2:
        return False
    if cleaned in GENERIC_METADATA_VALUES:
        return False
    if cleaned.startswith("c:\\") or cleaned.startswith("d:\\") or cleaned.startswith("/"):
        return False
    return True


def parse_from_filename_and_path(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Fallback resolver using Regex heuristics on filename and folder hierarchy.
    Cleans up hyphens, underscores, numbering artifacts, and publisher tags.
    """
    filename = os.path.basename(file_path)
    base_name, _ = os.path.splitext(filename)
    normalized_path = file_path.replace("\\", "/").lower()

    # Step 1: Detect author from parent folder hierarchy if known
    author_candidate: Optional[str] = None
    for key, auth_name in KNOWN_AUTHORS_MAP.items():
        if f"/{key}/" in normalized_path or f"/{key}-" in normalized_path or key in normalized_path:
            author_candidate = auth_name
            break

    # Step 2: Clean up filename noise patterns
    cleaned_name = base_name
    # Remove common publisher / format tags
    noise_patterns = [
        r"-pdf$", r"_pdf$", r"\.pdf$", r"-epub$", r"-docx$",
        r"-KaynakYayinlari", r"-IsikAkademiY-pdf", r"-IsikYayinlari", r"-ZAMAN",
        r"-U\d+", r"-\d+$", r"\(\d+\)$"
    ]
    for pattern in noise_patterns:
        cleaned_name = re.sub(pattern, "", cleaned_name, flags=re.IGNORECASE)

    # Step 3: Check for "Author - Title" or "Title - Author" in filename
    # e.g., "Haris-El-Muhasibi-Er-Riaye-1" or "Osmanlılarda-Hilafet-Mustafa-Alkan"
    title_candidate = cleaned_name

    # Check for author separator (hyphen, dash, en-dash)
    if " - " in cleaned_name:
        parts = cleaned_name.split(" - ", 1)
        part1, part2 = parts[0].strip(), parts[1].strip()
        if not author_candidate:
            # Check which part looks like an author name
            author_candidate = part1
            title_candidate = part2
        else:
            title_candidate = part2 if author_candidate.lower() in part1.lower() else part1
    elif "-" in cleaned_name and not author_candidate:
        # e.g. "Ahirzaman-ve-Kiyamet-Alametleri-Ayhan-Tekines"
        tokens = [t.strip() for t in cleaned_name.split("-") if t.strip()]
        if len(tokens) >= 3:
            # Check if last 2 tokens match a known author or plausible name
            last_two = f"{tokens[-2]} {tokens[-1]}".lower()
            if last_two in KNOWN_AUTHORS_MAP:
                author_candidate = KNOWN_AUTHORS_MAP[last_two]
                title_candidate = " ".join(tokens[:-2])
            else:
                first_two = f"{tokens[0]} {tokens[1]}".lower()
                if first_two in KNOWN_AUTHORS_MAP:
                    author_candidate = KNOWN_AUTHORS_MAP[first_two]
                    title_candidate = " ".join(tokens[2:])

    # Final formatting of title
    title_candidate = title_candidate.replace("-", " ").replace("_", " ")
    title_candidate = re.sub(r"\s+", " ", title_candidate).strip()

    # If title is empty, fallback to base filename
    if not title_candidate:
        title_candidate = base_name.replace("_", " ").replace("-", " ").strip()

    return title_candidate, author_candidate


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata and page count from PDF using PyMuPDF (fitz) or pypdf.
    """
    title = None
    author = None
    page_count = None

    # Try PyMuPDF if installed
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(file_path)
            meta = doc.metadata or {}
            title = meta.get("title")
            author = meta.get("author")
            page_count = doc.page_count
            doc.close()
        except Exception:
            pass

    # Try pypdf if PyMuPDF failed or is unavailable
    if (page_count is None or not title) and HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(file_path, strict=False)
            page_count = len(reader.pages)
            meta = reader.metadata
            if meta:
                if not title and meta.title:
                    title = meta.title
                if not author and meta.author:
                    author = meta.author
        except Exception:
            pass

    return {
        "title": clean_string(title),
        "author": clean_string(author),
        "page_count": page_count
    }


def extract_epub_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata (title, author/creator, chapter/document count) from EPUB files.
    Uses pure-Python zipfile parsing with fallback to ebooklib.
    """
    title = None
    author = None
    page_count = None

    # 1. Pure Python zipfile and OPF parser (Fast, robust, no C-dependencies)
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Find container.xml to locate rootfile .opf
            try:
                container_data = zf.read('META-INF/container.xml')
                c_root = ET.fromstring(container_data)
                # Find rootfile with full-path
                opf_path = ""
                for elem in c_root.iter():
                    if elem.tag.endswith("rootfile") and "full-path" in elem.attrib:
                        opf_path = elem.attrib["full-path"]
                        break
            except Exception:
                opf_path = ""

            # If container lookup failed, find first .opf file in archive
            if not opf_path:
                for name in zf.namelist():
                    if name.lower().endswith(".opf"):
                        opf_path = name
                        break

            if opf_path and opf_path in zf.namelist():
                opf_data = zf.read(opf_path)
                soup = BeautifulSoup(opf_data, "xml")

                # Extract title
                title_elem = soup.find(["dc:title", "title"])
                if title_elem and title_elem.text:
                    title = title_elem.text.strip()

                # Extract author / creator
                creator_elem = soup.find(["dc:creator", "creator"])
                if creator_elem and creator_elem.text:
                    author = creator_elem.text.strip()

                # Count spine itemrefs or manifest items (approximates chapter/page count)
                spine_items = soup.find_all(["itemref", "spine"])
                if spine_items:
                    page_count = len(spine_items)
                else:
                    # Count html/xhtml documents in manifest
                    html_files = [
                        n for n in zf.namelist()
                        if n.lower().endswith(('.xhtml', '.html', '.htm'))
                    ]
                    page_count = len(html_files) if html_files else None
    except Exception:
        pass

    # 2. Try ebooklib if available and metadata missing
    if (not title or not author) and HAS_EBOOKLIB:
        try:
            book = epub.read_epub(file_path, options={"ignore_ncx": True})
            if not title:
                t_meta = book.get_metadata('DC', 'title')
                if t_meta:
                    title = t_meta[0][0]
            if not author:
                c_meta = book.get_metadata('DC', 'creator')
                if c_meta:
                    author = c_meta[0][0]
            if page_count is None:
                docs = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
                page_count = len(docs) if docs else None
        except Exception:
            pass

    return {
        "title": clean_string(title),
        "author": clean_string(author),
        "page_count": page_count
    }


def extract_docx_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata (title, author, paragraph/page count) from Word (.docx) files.
    """
    title = None
    author = None
    page_count = None

    # Try python-docx if installed
    if HAS_DOCX:
        try:
            doc = docx.Document(file_path)
            props = doc.core_properties
            title = props.title
            author = props.author
            page_count = len(doc.paragraphs)
        except Exception:
            pass

    # Pure Python zipfile fallback for .docx (Office Open XML)
    if not title or page_count is None:
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Core properties
                if 'docProps/core.xml' in zf.namelist():
                    core_xml = zf.read('docProps/core.xml')
                    root = ET.fromstring(core_xml)
                    for elem in root.iter():
                        tag = elem.tag.lower()
                        if tag.endswith("title") and elem.text and not title:
                            title = elem.text.strip()
                        elif (tag.endswith("creator") or tag.endswith("lastmodifiedby")) and elem.text and not author:
                            author = elem.text.strip()

                # App properties for page/paragraph counts
                if 'docProps/app.xml' in zf.namelist():
                    app_xml = zf.read('docProps/app.xml')
                    app_root = ET.fromstring(app_xml)
                    for elem in app_root.iter():
                        tag = elem.tag.lower()
                        if tag.endswith("pages") and elem.text and elem.text.isdigit():
                            pages = int(elem.text)
                            if pages > 0:
                                page_count = pages
                                break
                        elif tag.endswith("paragraphs") and elem.text and elem.text.isdigit():
                            if page_count is None:
                                page_count = int(elem.text)
        except Exception:
            pass

    return {
        "title": clean_string(title),
        "author": clean_string(author),
        "page_count": page_count
    }


def extract_metadata(file_path: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Master extractor function:
    1. Computes 64 KB SHA-256 hash.
    2. Identifies file extension and format.
    3. Extracts document metadata via format-specific extractor.
    4. Applies smart regex and folder hierarchy fallback for missing titles/authors.
    5. Returns formatted dictionary ready for database insertion.
    """
    stat = os.stat(file_path)
    file_size_bytes = stat.st_size
    sha256_hash = calculate_sha256(file_path)

    _, ext = os.path.splitext(file_path)
    file_type = ext.lower().replace(".", "")
    if not file_type:
        file_type = "unknown"

    extracted: Dict[str, Any] = {"title": None, "author": None, "page_count": None}

    if file_type == "pdf":
        extracted = extract_pdf_metadata(file_path)
    elif file_type == "epub":
        extracted = extract_epub_metadata(file_path)
    elif file_type in ("docx", "doc"):
        extracted = extract_docx_metadata(file_path)

    title = extracted.get("title")
    author = extracted.get("author")
    page_count = extracted.get("page_count")

    # If title or author is invalid or generic, use fallback resolver
    fb_title, fb_author = parse_from_filename_and_path(file_path)

    if not is_valid_metadata_value(title):
        title = fb_title

    if not is_valid_metadata_value(author):
        author = fb_author

    # Format file path (relative if base_dir is provided, else relative to cwd)
    if base_dir:
        try:
            rel_path = os.path.relpath(file_path, base_dir)
        except ValueError:
            rel_path = file_path
    else:
        try:
            rel_path = os.path.relpath(file_path, os.getcwd())
        except ValueError:
            rel_path = file_path

    return {
        "title": title or fb_title or os.path.basename(file_path),
        "author": author,
        "page_count": page_count,
        "file_type": file_type,
        "file_path": rel_path.replace("\\", "/"),
        "file_size_bytes": file_size_bytes,
        "sha256_hash": sha256_hash
    }
