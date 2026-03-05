#!/bin/bash

# FileToFlashcards Web App Launcher
# ===========================

echo ""
echo "======================================"
echo "  FileToFlashcards Web App"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3 from https://www.python.org/"
    exit 1
fi

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check for tesseract (needed for OCR)
if ! command -v tesseract &> /dev/null; then
    echo ""
    echo "Warning: Tesseract OCR is not installed."
    echo "Image OCR will not work without it."
    echo ""
    echo "To install Tesseract:"
    echo "  macOS:   brew install tesseract"
    echo "  Ubuntu:  sudo apt-get install tesseract-ocr"
    echo "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
    echo ""
fi

echo ""
echo "Starting server..."
echo "Open http://localhost:8080 in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"
echo ""

python3 app.py
