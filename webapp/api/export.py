"""
Vercel Serverless Function: Export to Anki Deck
"""

import json
import sqlite3
import tempfile
import zipfile
import hashlib
import random
import string
import time
import base64
import os
from http.server import BaseHTTPRequestHandler


def generate_guid():
    """Generate a random GUID for Anki."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))


def checksum(text):
    """Calculate checksum for Anki."""
    return int(hashlib.sha1(text.encode('utf-8')).hexdigest()[:8], 16)


def create_anki_deck(deck_name, flashcards):
    """Create an Anki .apkg file from flashcards."""

    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'collection.anki2')
    media_path = os.path.join(temp_dir, 'media')

    with open(media_path, 'w') as f:
        f.write('{}')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS col (
            id integer primary key, crt integer not null, mod integer not null,
            scm integer not null, ver integer not null, dty integer not null,
            usn integer not null, ls integer not null, conf text not null,
            models text not null, decks text not null, dconf text not null, tags text not null
        );
        CREATE TABLE IF NOT EXISTS notes (
            id integer primary key, guid text not null, mid integer not null,
            mod integer not null, usn integer not null, tags text not null,
            flds text not null, sfld integer not null, csum integer not null,
            flags integer not null, data text not null
        );
        CREATE TABLE IF NOT EXISTS cards (
            id integer primary key, nid integer not null, did integer not null,
            ord integer not null, mod integer not null, usn integer not null,
            type integer not null, queue integer not null, due integer not null,
            ivl integer not null, factor integer not null, reps integer not null,
            lapses integer not null, left integer not null, odue integer not null,
            odid integer not null, flags integer not null, data text not null
        );
        CREATE TABLE IF NOT EXISTS revlog (
            id integer primary key, cid integer not null, usn integer not null,
            ease integer not null, ivl integer not null, lastIvl integer not null,
            factor integer not null, time integer not null, type integer not null
        );
        CREATE TABLE IF NOT EXISTS graves (usn integer not null, oid integer not null, type integer not null);
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

    conf = json.dumps({"activeDecks": [1], "curDeck": 1, "newSpread": 0, "collapseTime": 1200, "timeLim": 0, "estTimes": True, "dueCounts": True, "curModel": None, "nextPos": 1, "sortType": "noteFld", "sortBackwards": False, "addToCur": True})

    models = json.dumps({
        str(model_id): {
            "id": model_id, "name": "Basic", "type": 0, "mod": now, "usn": -1, "sortf": 0, "did": 1,
            "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": "{{Front}}", "afmt": "{{FrontSide}}<hr id=answer>{{Back}}", "bqfmt": "", "bafmt": "", "did": None, "bfont": "", "bsize": 0}],
            "flds": [{"name": "Front", "ord": 0, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []}, {"name": "Back", "ord": 1, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []}],
            "css": ".card {font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white;}",
            "latexPre": "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n",
            "latexPost": "\n\\end{document}", "latexsvg": False, "req": [[0, "any", [0]]]
        }
    })

    decks = json.dumps({
        "1": {"id": 1, "name": "Default", "mod": now, "usn": -1, "lrnToday": [0, 0], "revToday": [0, 0], "newToday": [0, 0], "timeToday": [0, 0], "collapsed": False, "browserCollapsed": False, "desc": "", "dyn": 0, "conf": 1, "extendNew": 0, "extendRev": 0},
        str(deck_id): {"id": deck_id, "name": deck_name, "mod": now, "usn": -1, "lrnToday": [0, 0], "revToday": [0, 0], "newToday": [0, 0], "timeToday": [0, 0], "collapsed": False, "browserCollapsed": False, "desc": "", "dyn": 0, "conf": 1, "extendNew": 0, "extendRev": 0}
    })

    dconf = json.dumps({"1": {"id": 1, "name": "Default", "mod": 0, "usn": 0, "maxTaken": 60, "autoplay": True, "timer": 0, "replayq": True, "new": {"bury": False, "delays": [1, 10], "initialFactor": 2500, "ints": [1, 4, 0], "order": 1, "perDay": 20}, "rev": {"bury": False, "ease4": 1.3, "ivlFct": 1, "maxIvl": 36500, "perDay": 200, "hardFactor": 1.2}, "lapse": {"delays": [10], "leechAction": 1, "leechFails": 8, "minInt": 1, "mult": 0}, "dyn": False}})

    cursor.execute('INSERT INTO col VALUES (1, ?, ?, ?, 11, 0, 0, 0, ?, ?, ?, ?, ?)', (now, now * 1000, now * 1000, conf, models, decks, dconf, '{}'))

    for i, card in enumerate(flashcards):
        note_id = deck_id + i + 100
        card_id = deck_id + i + 1000
        guid = generate_guid()
        front = card.get('front', '')
        back = card.get('back', '')
        flds = f"{front}\x1f{back}"
        csum = checksum(front)
        cursor.execute('INSERT INTO notes VALUES (?, ?, ?, ?, -1, ?, ?, ?, ?, 0, ?)', (note_id, guid, model_id, now, '', flds, front, csum, ''))
        cursor.execute('INSERT INTO cards VALUES (?, ?, ?, 0, ?, -1, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 0, ?)', (card_id, note_id, deck_id, now, i, ''))

    conn.commit()
    conn.close()

    apkg_path = os.path.join(temp_dir, f"{deck_name}.apkg")
    with zipfile.ZipFile(apkg_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, 'collection.anki2')
        zf.write(media_path, 'media')

    with open(apkg_path, 'rb') as f:
        apkg_data = f.read()

    # Cleanup
    os.unlink(db_path)
    os.unlink(media_path)
    os.unlink(apkg_path)
    os.rmdir(temp_dir)

    return apkg_data


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            return

        if not data.get('flashcards'):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No flashcards provided'}).encode())
            return

        deck_name = data.get('deck_name', 'Imported Deck')
        deck_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not deck_name:
            deck_name = 'Imported Deck'

        try:
            apkg_data = create_anki_deck(deck_name, data['flashcards'])

            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{deck_name}.apkg"')
            self.end_headers()
            self.wfile.write(apkg_data)

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
