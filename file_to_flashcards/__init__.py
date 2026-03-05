"""
FileToFlashcards Anki Add-On
Import files and generate flashcards using Claude AI.
"""

import sys
from pathlib import Path

# Add vendor directory to path for bundled dependencies
vendor_dir = Path(__file__).parent / "vendor"
if vendor_dir.exists():
    vendor_str = str(vendor_dir)
    if vendor_str not in sys.path:
        sys.path.insert(0, vendor_str)
    print(f"[FileToFlashcards] Vendor dir added: {vendor_str}")
    print(f"[FileToFlashcards] sys.path[0]: {sys.path[0]}")
else:
    print(f"[FileToFlashcards] WARNING: Vendor dir not found: {vendor_dir}")

# Test imports
try:
    import anthropic
    print(f"[FileToFlashcards] anthropic imported successfully from {anthropic.__file__}")
except ImportError as e:
    print(f"[FileToFlashcards] ERROR importing anthropic: {e}")

try:
    import fitz
    print(f"[FileToFlashcards] fitz (PyMuPDF) imported successfully")
except ImportError as e:
    print(f"[FileToFlashcards] ERROR importing fitz: {e}")

try:
    import docx
    print(f"[FileToFlashcards] docx imported successfully")
except ImportError as e:
    print(f"[FileToFlashcards] ERROR importing docx: {e}")

from aqt import mw
from aqt.qt import QAction
from .main import show_dialog


def setup_menu():
    """Add FileToFlashcards to the Tools menu."""
    action = QAction("FileToFlashcards...", mw)
    action.triggered.connect(show_dialog)
    mw.form.menuTools.addAction(action)


setup_menu()
