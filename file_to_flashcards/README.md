# FileToFlashcards Anki Add-On

Import files (PDF, DOCX, TXT, images) and generate Anki flashcards using Claude AI.

## Installation

### Method 1: Manual Installation

1. Find your Anki add-ons folder:
   - **Windows**: `%APPDATA%\Anki2\addons21\`
   - **macOS**: `~/Library/Application Support/Anki2/addons21/`
   - **Linux**: `~/.local/share/Anki2/addons21/`

2. Copy the `file_to_flashcards` folder into the addons21 directory

3. Restart Anki

### Method 2: Install from .ankiaddon file

1. Create the package: see "Creating .ankiaddon Package" below
2. In Anki, go to Tools → Add-ons → Install from file
3. Select the `.ankiaddon` file
4. Restart Anki

## Dependencies

### Required
- `anthropic` - Claude API client
  ```
  pip install anthropic
  ```

### Optional (for file format support)
- `PyMuPDF` - PDF support
  ```
  pip install PyMuPDF
  ```
- `python-docx` - DOCX support
  ```
  pip install python-docx
  ```
- `Pillow` + `pytesseract` - Image OCR support
  ```
  pip install Pillow pytesseract
  ```
  Note: pytesseract requires Tesseract OCR to be installed on your system
- `striprtf` - RTF support
  ```
  pip install striprtf
  ```

## Usage

1. Open Anki
2. Go to **Tools → FileToFlashcards...**
3. Enter your Claude API key (get one at https://console.anthropic.com/)
4. Click **Browse** and select a file
5. Choose the target deck and max cards
6. Click **Generate Flashcards**
7. Review the generated cards (uncheck any you don't want)
8. Click **Import to Anki**

## Supported File Formats

- **PDF** (.pdf) - Requires PyMuPDF
- **Word** (.docx, .doc) - Requires python-docx
- **Plain Text** (.txt) - Always available
- **RTF** (.rtf) - Requires striprtf
- **Images** (.png, .jpg, .jpeg, .gif, .bmp, .tiff) - Requires Pillow + pytesseract

## Configuration

Settings are saved automatically and persist between sessions:
- API Key
- Default deck
- Max cards per file

You can also edit settings via Tools → Add-ons → FileToFlashcards → Config

## Creating .ankiaddon Package

To distribute the add-on:

```bash
cd /path/to/addons21
rm -rf file_to_flashcards/__pycache__
zip -r file_to_flashcards.ankiaddon file_to_flashcards/*
```

## Troubleshooting

### "anthropic package not installed"
Run: `pip install anthropic`

### "No text content found in file"
- For PDFs: Make sure PyMuPDF is installed
- For images: Make sure Pillow and pytesseract are installed, and Tesseract OCR is on your system

### Cards not appearing
- Click "Reset" in the main Anki window
- Check the deck you selected exists

## License

MIT License
