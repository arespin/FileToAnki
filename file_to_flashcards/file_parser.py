"""
File parsing module for extracting text from various file formats.
Supports PDF, DOCX, TXT, RTF, and images (with OCR).
"""

from pathlib import Path

# Track available dependencies
AVAILABLE_PARSERS = {
    'pdf': False,
    'docx': False,
    'image': False,
    'rtf': False,
}

# Try importing optional dependencies
try:
    import fitz  # PyMuPDF
    AVAILABLE_PARSERS['pdf'] = True
except ImportError:
    fitz = None

try:
    from docx import Document as DocxDocument
    AVAILABLE_PARSERS['docx'] = True
except ImportError:
    DocxDocument = None

try:
    from PIL import Image
    import pytesseract
    AVAILABLE_PARSERS['image'] = True
except ImportError:
    Image = None
    pytesseract = None

try:
    from striprtf.striprtf import rtf_to_text
    AVAILABLE_PARSERS['rtf'] = True
except ImportError:
    rtf_to_text = None


def get_supported_extensions():
    """Return list of supported file extensions based on available dependencies."""
    extensions = ['txt']  # Always supported

    if AVAILABLE_PARSERS['pdf']:
        extensions.append('pdf')
    if AVAILABLE_PARSERS['docx']:
        extensions.extend(['docx', 'doc'])
    if AVAILABLE_PARSERS['image']:
        extensions.extend(['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'])
    if AVAILABLE_PARSERS['rtf']:
        extensions.append('rtf')

    return extensions


def get_file_filter():
    """Return file filter string for QFileDialog."""
    exts = get_supported_extensions()
    ext_pattern = ' '.join(f'*.{ext}' for ext in exts)
    return f"Supported Files ({ext_pattern});;All Files (*)"


def parse_pdf(file_path):
    """Extract text from PDF using PyMuPDF."""
    if not fitz:
        raise ImportError("PyMuPDF (fitz) not installed. Install with: pip install PyMuPDF")

    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text() + "\n\n"
        doc.close()

        # If no text extracted, try OCR
        if not text.strip() and AVAILABLE_PARSERS['image']:
            text = ocr_pdf(file_path)
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {str(e)}")
    return text


def ocr_pdf(file_path):
    """OCR a PDF by converting pages to images."""
    if not fitz or not Image or not pytesseract:
        return ""

    text = ""
    try:
        doc = fitz.open(file_path)
        for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img) + "\n\n"
        doc.close()
    except Exception as e:
        print(f"OCR failed: {e}")
    return text


def parse_txt(file_path):
    """Read plain text file with multiple encoding fallbacks."""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise Exception("Failed to decode text file")


def parse_rtf(file_path):
    """Extract text from RTF file."""
    if rtf_to_text:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            rtf_content = f.read()
        return rtf_to_text(rtf_content)
    else:
        # Fallback: basic RTF stripping
        import re
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        content = re.sub(r'\\[a-z]+\d*\s?', '', content)
        content = re.sub(r'[{}]', '', content)
        return content


def parse_docx(file_path):
    """Extract text from DOCX file."""
    if not DocxDocument:
        raise ImportError("python-docx not installed. Install with: pip install python-docx")

    try:
        doc = DocxDocument(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        raise Exception(f"Failed to parse DOCX: {str(e)}")


def parse_image(file_path):
    """OCR an image file."""
    if not Image or not pytesseract:
        raise ImportError("Pillow and pytesseract not installed. Install with: pip install Pillow pytesseract")

    try:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        raise Exception(f"Failed to OCR image: {str(e)}")


def parse_file(file_path):
    """Parse any supported file and return extracted text."""
    ext = Path(file_path).suffix.lower().lstrip('.')

    if ext == 'pdf':
        return parse_pdf(file_path)
    elif ext == 'txt':
        return parse_txt(file_path)
    elif ext == 'rtf':
        return parse_rtf(file_path)
    elif ext in ('docx', 'doc'):
        return parse_docx(file_path)
    elif ext in ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'):
        return parse_image(file_path)
    else:
        # Try as plain text
        return parse_txt(file_path)


def get_missing_dependencies():
    """Return list of missing optional dependencies with install instructions."""
    missing = []
    if not AVAILABLE_PARSERS['pdf']:
        missing.append("PyMuPDF (pip install PyMuPDF) - for PDF support")
    if not AVAILABLE_PARSERS['docx']:
        missing.append("python-docx (pip install python-docx) - for DOCX support")
    if not AVAILABLE_PARSERS['image']:
        missing.append("Pillow + pytesseract (pip install Pillow pytesseract) - for image OCR")
    if not AVAILABLE_PARSERS['rtf']:
        missing.append("striprtf (pip install striprtf) - for RTF support")
    return missing
