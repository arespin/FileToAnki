#!/usr/bin/env python3
"""
FileToAnki Web App
A web application that extracts facts from uploaded files and converts them to Anki decks.
"""

import os
import json
import sqlite3
import tempfile
import zipfile
import hashlib
import random
import string
import time
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import anthropic

# File parsing imports
import fitz  # PyMuPDF for PDF
from docx import Document as DocxDocument
from PIL import Image
import pytesseract

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'rtf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# File Parsing
# ============================================================================

def parse_pdf(file_path):
    """Extract text from PDF using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text() + "\n\n"
        doc.close()

        # If no text extracted, try OCR
        if not text.strip():
            text = ocr_pdf(file_path)
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {str(e)}")
    return text


def ocr_pdf(file_path):
    """OCR a PDF by converting pages to images."""
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
        # Fallback: basic RTF stripping
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Very basic RTF to text
        import re
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


# ============================================================================
# Claude API
# ============================================================================

def extract_flashcards(text, api_key, max_cards=25):
    """Use Claude to extract flashcards from text."""
    client = anthropic.Anthropic(api_key=api_key)

    # Truncate if too long
    max_length = 50000
    if len(text) > max_length:
        text = text[:max_length] + "\n[Text truncated...]"

    prompt = f"""Analyze the following text and extract the {max_cards} most important facts, concepts, and pieces of information worth memorizing.

For each fact, create a flashcard with:
- "front": A clear, specific question or prompt
- "back": A concise, accurate answer

Guidelines:
- Focus on key concepts, definitions, important facts, dates, formulas, and relationships
- Questions should be specific and unambiguous
- Answers should be concise but complete
- Avoid trivial or obvious information
- Each card should test ONE concept

Return ONLY a valid JSON array of flashcard objects. No other text or explanation.
Format: [{{"front": "question", "back": "answer"}}, ...]

TEXT TO ANALYZE:
---
{text}
---

JSON flashcards:"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()

    # Extract JSON from response
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    # Find JSON array
    start = response_text.find('[')
    end = response_text.rfind(']') + 1
    if start != -1 and end > start:
        response_text = response_text[start:end]

    try:
        flashcards = json.loads(response_text)
        return flashcards
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Claude response: {str(e)}")


# ============================================================================
# Anki Export
# ============================================================================

def generate_guid():
    """Generate a random GUID for Anki."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))


def checksum(text):
    """Calculate checksum for Anki."""
    return int(hashlib.sha1(text.encode('utf-8')).hexdigest()[:8], 16)


def create_anki_deck(deck_name, flashcards):
    """Create an Anki .apkg file from flashcards."""

    # Create temp directory for the deck
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'collection.anki2')
    media_path = os.path.join(temp_dir, 'media')

    # Write empty media file
    with open(media_path, 'w') as f:
        f.write('{}')

    # Create SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS col (
            id integer primary key,
            crt integer not null,
            mod integer not null,
            scm integer not null,
            ver integer not null,
            dty integer not null,
            usn integer not null,
            ls integer not null,
            conf text not null,
            models text not null,
            decks text not null,
            dconf text not null,
            tags text not null
        );
        CREATE TABLE IF NOT EXISTS notes (
            id integer primary key,
            guid text not null,
            mid integer not null,
            mod integer not null,
            usn integer not null,
            tags text not null,
            flds text not null,
            sfld integer not null,
            csum integer not null,
            flags integer not null,
            data text not null
        );
        CREATE TABLE IF NOT EXISTS cards (
            id integer primary key,
            nid integer not null,
            did integer not null,
            ord integer not null,
            mod integer not null,
            usn integer not null,
            type integer not null,
            queue integer not null,
            due integer not null,
            ivl integer not null,
            factor integer not null,
            reps integer not null,
            lapses integer not null,
            left integer not null,
            odue integer not null,
            odid integer not null,
            flags integer not null,
            data text not null
        );
        CREATE TABLE IF NOT EXISTS revlog (
            id integer primary key,
            cid integer not null,
            usn integer not null,
            ease integer not null,
            ivl integer not null,
            lastIvl integer not null,
            factor integer not null,
            time integer not null,
            type integer not null
        );
        CREATE TABLE IF NOT EXISTS graves (
            usn integer not null,
            oid integer not null,
            type integer not null
        );
        CREATE INDEX IF NOT EXISTS ix_notes_usn on notes (usn);
        CREATE INDEX IF NOT EXISTS ix_cards_usn on cards (usn);
        CREATE INDEX IF NOT EXISTS ix_revlog_usn on revlog (usn);
        CREATE INDEX IF NOT EXISTS ix_cards_nid on cards (nid);
        CREATE INDEX IF NOT EXISTS ix_cards_sched on cards (did, queue, due);
        CREATE INDEX IF NOT EXISTS ix_revlog_cid on revlog (cid);
        CREATE INDEX IF NOT EXISTS ix_notes_csum on notes (csum);
    ''')

    now = int(time.time())
    deck_id = int(time.time() * 1000)
    model_id = deck_id + 1

    # Collection configuration
    conf = json.dumps({
        "activeDecks": [1],
        "curDeck": 1,
        "newSpread": 0,
        "collapseTime": 1200,
        "timeLim": 0,
        "estTimes": True,
        "dueCounts": True,
        "curModel": None,
        "nextPos": 1,
        "sortType": "noteFld",
        "sortBackwards": False,
        "addToCur": True
    })

    # Models (note types)
    models = json.dumps({
        str(model_id): {
            "id": model_id,
            "name": "Basic",
            "type": 0,
            "mod": now,
            "usn": -1,
            "sortf": 0,
            "did": 1,
            "tmpls": [{
                "name": "Card 1",
                "ord": 0,
                "qfmt": "{{Front}}",
                "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
                "bqfmt": "",
                "bafmt": "",
                "did": None,
                "bfont": "",
                "bsize": 0
            }],
            "flds": [
                {"name": "Front", "ord": 0, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []},
                {"name": "Back", "ord": 1, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []}
            ],
            "css": ".card {font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white;}",
            "latexPre": "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n",
            "latexPost": "\n\\end{document}",
            "latexsvg": False,
            "req": [[0, "any", [0]]]
        }
    })

    # Decks
    decks = json.dumps({
        "1": {
            "id": 1,
            "name": "Default",
            "mod": now,
            "usn": -1,
            "lrnToday": [0, 0],
            "revToday": [0, 0],
            "newToday": [0, 0],
            "timeToday": [0, 0],
            "collapsed": False,
            "browserCollapsed": False,
            "desc": "",
            "dyn": 0,
            "conf": 1,
            "extendNew": 0,
            "extendRev": 0
        },
        str(deck_id): {
            "id": deck_id,
            "name": deck_name,
            "mod": now,
            "usn": -1,
            "lrnToday": [0, 0],
            "revToday": [0, 0],
            "newToday": [0, 0],
            "timeToday": [0, 0],
            "collapsed": False,
            "browserCollapsed": False,
            "desc": "",
            "dyn": 0,
            "conf": 1,
            "extendNew": 0,
            "extendRev": 0
        }
    })

    # Deck configuration
    dconf = json.dumps({
        "1": {
            "id": 1,
            "name": "Default",
            "mod": 0,
            "usn": 0,
            "maxTaken": 60,
            "autoplay": True,
            "timer": 0,
            "replayq": True,
            "new": {
                "bury": False,
                "delays": [1, 10],
                "initialFactor": 2500,
                "ints": [1, 4, 0],
                "order": 1,
                "perDay": 20
            },
            "rev": {
                "bury": False,
                "ease4": 1.3,
                "ivlFct": 1,
                "maxIvl": 36500,
                "perDay": 200,
                "hardFactor": 1.2
            },
            "lapse": {
                "delays": [10],
                "leechAction": 1,
                "leechFails": 8,
                "minInt": 1,
                "mult": 0
            },
            "dyn": False
        }
    })

    # Insert collection
    cursor.execute('''
        INSERT INTO col VALUES (1, ?, ?, ?, 11, 0, 0, 0, ?, ?, ?, ?, '{}')
    ''', (now, now * 1000, now * 1000, conf, models, decks, dconf))

    # Insert notes and cards
    for i, card in enumerate(flashcards):
        note_id = deck_id + i + 100
        card_id = deck_id + i + 1000
        guid = generate_guid()
        front = card.get('front', '')
        back = card.get('back', '')
        flds = f"{front}\x1f{back}"
        csum = checksum(front)

        cursor.execute('''
            INSERT INTO notes VALUES (?, ?, ?, ?, -1, '', ?, ?, ?, 0, '')
        ''', (note_id, guid, model_id, now, flds, front, csum))

        cursor.execute('''
            INSERT INTO cards VALUES (?, ?, ?, 0, ?, -1, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 0, '')
        ''', (card_id, note_id, deck_id, now, i))

    conn.commit()
    conn.close()

    # Create .apkg (zip file)
    apkg_path = os.path.join(temp_dir, f"{deck_name}.apkg")
    with zipfile.ZipFile(apkg_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, 'collection.anki2')
        zf.write(media_path, 'media')

    return apkg_path


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and parse a file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported'}), 400

    try:
        filename = secure_filename(file.filename)
        file_path = app.config['UPLOAD_FOLDER'] / filename
        file.save(file_path)

        # Parse the file
        text = parse_file(str(file_path))

        # Clean up
        os.remove(file_path)

        if not text.strip():
            return jsonify({'error': 'No text content found in file'}), 400

        return jsonify({
            'success': True,
            'filename': filename,
            'text_length': len(text),
            'text_preview': text[:500] + '...' if len(text) > 500 else text,
            'text': text
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/extract', methods=['POST'])
def extract():
    """Extract flashcards from text using Claude."""
    data = request.json

    if not data.get('text'):
        return jsonify({'error': 'No text provided'}), 400

    if not data.get('api_key'):
        return jsonify({'error': 'No API key provided'}), 400

    try:
        # Validate max_cards
        max_cards = data.get('max_cards', 25)
        try:
            max_cards = int(max_cards)
            max_cards = max(1, min(100, max_cards))  # Clamp between 1 and 100
        except (TypeError, ValueError):
            max_cards = 25

        flashcards = extract_flashcards(
            data['text'],
            data['api_key'],
            max_cards=max_cards
        )

        return jsonify({
            'success': True,
            'flashcards': flashcards,
            'count': len(flashcards)
        })

    except anthropic.AuthenticationError:
        return jsonify({'error': 'Invalid API key'}), 401
    except anthropic.RateLimitError:
        return jsonify({'error': 'Rate limited. Please try again later.'}), 429
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export', methods=['POST'])
def export():
    """Export flashcards to Anki deck."""
    data = request.json

    if not data.get('flashcards'):
        return jsonify({'error': 'No flashcards provided'}), 400

    deck_name = data.get('deck_name', 'Imported Deck')
    # Sanitize deck name
    deck_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not deck_name:
        deck_name = 'Imported Deck'

    try:
        apkg_path = create_anki_deck(deck_name, data['flashcards'])

        return send_file(
            apkg_path,
            as_attachment=True,
            download_name=f"{deck_name}.apkg",
            mimetype='application/octet-stream'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*50)
    print("FileToAnki Web App")
    print("="*50)
    print("\nOpen http://localhost:8080 in your browser")
    print("\nPress Ctrl+C to stop the server")
    print("="*50 + "\n")

    app.run(debug=False, host='0.0.0.0', port=8080)
