# FileToAnki

Convert any document into Anki flashcards using AI. Upload a file, extract key facts with Claude, and export a ready-to-use Anki deck.

## Features

- **Multi-format support**: PDF, TXT, DOCX, RTF, and images (with OCR)
- **AI-powered extraction**: Uses Claude to identify and extract the most important facts
- **Smart flashcard generation**: Creates question/answer pairs optimized for learning
- **Native Anki export**: Generates `.apkg` files compatible with Anki desktop and mobile
- **Edit before export**: Review, edit, add, or delete cards before exporting

## Two Ways to Use

### 1. Web App (Recommended for quick use)

A Flask-based web application that runs locally in your browser.

![Web App Screenshot](https://via.placeholder.com/800x400?text=FileToAnki+Web+App)

#### Requirements

- Python 3.8+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (optional, for image OCR)
- Claude API key from [Anthropic](https://console.anthropic.com/)

#### Installation

```bash
cd webapp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Tesseract for image OCR
# macOS:
brew install tesseract
# Ubuntu:
sudo apt-get install tesseract-ocr
```

#### Run

```bash
python app.py
```

Open **http://localhost:8080** in your browser.

---

### 2. iOS App

A native SwiftUI app for iPhone and iPad.

#### Requirements

- macOS with Xcode 15+
- iOS 15+ device or simulator
- Claude API key from [Anthropic](https://console.anthropic.com/)

#### Run

1. Open `FileToAnki.xcodeproj` in Xcode
2. Select your development team in Signing & Capabilities
3. Build and run on a simulator or device
4. Enter your Claude API key when prompted

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │ ──▶ │   Parse     │ ──▶ │   Claude    │ ──▶ │   Export    │
│    File     │     │   Text      │     │   Extract   │     │   .apkg     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     PDF              Extract            AI identifies        SQLite DB
     DOCX             text from          key facts and        packaged as
     TXT              document           creates Q&A          Anki deck
     Images (OCR)                        pairs
```

1. **Upload**: Select any supported document
2. **Parse**: Text is extracted from the file (OCR for images/scanned PDFs)
3. **Extract**: Claude analyzes the content and generates flashcards
4. **Review**: Edit, add, or remove cards as needed
5. **Export**: Download the `.apkg` file and import into Anki

## Supported File Types

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text-based and scanned (via OCR) |
| Plain Text | `.txt` | UTF-8 encoded |
| Word | `.docx` | Microsoft Word documents |
| Rich Text | `.rtf` | Rich Text Format |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff` | Requires Tesseract OCR |

## API Key

This project requires a Claude API key from Anthropic:

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Create an account or sign in
3. Generate an API key
4. Enter the key in the app when prompted

**Privacy Note:** Your API key is stored locally in your browser's localStorage. When you extract flashcards, your key is sent securely over HTTPS to our server, which then forwards it to Anthropic's API. We do not store, log, or retain your API key on our servers.

## Project Structure

```
FileToAnki/
├── FileToAnki.xcodeproj/    # Xcode project
├── FileToAnki/              # iOS app source
│   ├── Models/              # Data models
│   ├── Views/               # SwiftUI views
│   ├── ViewModels/          # Business logic
│   └── Services/            # File parsing, API, export
├── webapp/                  # Web app source
│   ├── app.py              # Flask server
│   ├── templates/          # HTML templates
│   ├── requirements.txt    # Python dependencies
│   └── run.sh              # Launch script
└── README.md
```

## License

MIT License - feel free to use, modify, and distribute.

## Acknowledgments

- [Anthropic](https://www.anthropic.com/) for the Claude API
- [Anki](https://apps.ankiweb.net/) for the spaced repetition platform
