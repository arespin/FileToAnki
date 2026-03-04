"""
Vercel Serverless Function: File Upload and Parse
"""

import json
import tempfile
import os
from http.server import BaseHTTPRequestHandler

# File parsing imports
import fitz  # PyMuPDF for PDF
from docx import Document as DocxDocument
from PIL import Image

try:
    import pytesseract
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False


def parse_pdf(file_path):
    """Extract text from PDF using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text() + "\n\n"
        doc.close()
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {str(e)}")
    return text


def parse_txt(file_path):
    """Read plain text file."""
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
    try:
        from striprtf.striprtf import rtf_to_text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            rtf_content = f.read()
        return rtf_to_text(rtf_content)
    except ImportError:
        import re
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        content = re.sub(r'\\[a-z]+\d*\s?', '', content)
        content = re.sub(r'[{}]', '', content)
        return content


def parse_docx(file_path):
    """Extract text from DOCX file."""
    try:
        doc = DocxDocument(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        raise Exception(f"Failed to parse DOCX: {str(e)}")


def parse_image(file_path):
    """OCR an image file."""
    if not OCR_AVAILABLE:
        raise Exception("OCR not available on this server")
    try:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        raise Exception(f"Failed to OCR image: {str(e)}")


def parse_file(file_path, filename):
    """Parse any supported file and return extracted text."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

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
        return parse_txt(file_path)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        content_type = self.headers.get('Content-Type', '')

        if 'multipart/form-data' not in content_type:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Expected multipart/form-data'}).encode())
            return

        # Parse multipart data
        body = self.rfile.read(content_length)
        boundary = content_type.split('boundary=')[1].encode()

        parts = body.split(b'--' + boundary)
        file_data = None
        filename = None

        for part in parts:
            if b'filename=' in part:
                # Extract filename
                header_end = part.find(b'\r\n\r\n')
                header = part[:header_end].decode('utf-8', errors='ignore')
                for line in header.split('\r\n'):
                    if 'filename=' in line:
                        filename = line.split('filename=')[1].strip('"').strip("'")
                        break
                file_data = part[header_end + 4:].rstrip(b'\r\n--')

        if not file_data or not filename:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No file provided'}).encode())
            return

        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as f:
                f.write(file_data)
                temp_path = f.name

            # Parse the file
            text = parse_file(temp_path, filename)

            # Clean up
            os.unlink(temp_path)

            if not text.strip():
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'No text content found in file'}).encode())
                return

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'filename': filename,
                'text_length': len(text),
                'text_preview': text[:500] + '...' if len(text) > 500 else text,
                'text': text
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
