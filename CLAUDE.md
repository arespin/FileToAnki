# CLAUDE.md

This file provides context for Claude Code sessions working on this project.

## Project Overview

FileToAnki is a tool that converts documents into Anki flashcard decks using Claude AI. It exists as two implementations:

1. **iOS App** - Native SwiftUI app in `FileToAnki/`
2. **Web App** - Python Flask app in `webapp/`

Both implementations share the same core workflow: parse file → extract text → send to Claude API → generate flashcards → export as .apkg.

## Architecture

### iOS App (`FileToAnki/`)

```
FileToAnki/
├── FileToAnkiApp.swift      # App entry point, API key setup
├── Models/
│   ├── Flashcard.swift      # Q&A card model (Codable)
│   ├── Document.swift       # Parsed document with file type enum
│   └── AnkiDeck.swift       # Deck metadata
├── Views/
│   ├── ContentView.swift    # Main navigation + settings
│   ├── FilePickerView.swift # File upload UI
│   ├── ProcessingView.swift # Loading/progress animation
│   └── CardPreviewView.swift# Card list, editing, export
├── ViewModels/
│   └── DeckViewModel.swift  # Main business logic (@MainActor)
└── Services/
    ├── FileParserService.swift  # Multi-format text extraction
    ├── ClaudeService.swift      # Anthropic API client
    └── AnkiExportService.swift  # SQLite + ZIP generation
```

**Key patterns:**
- MVVM architecture
- `@MainActor` for UI-bound view models
- `async/await` for all async operations
- Services are stateless classes
- Views use `@StateObject` and `@ObservedObject`

### Web App (`webapp/`)

```
webapp/
├── app.py              # Flask server with all routes and logic
├── templates/
│   └── index.html      # Single-page app with vanilla JS
├── requirements.txt    # Python dependencies
└── run.sh             # Launch script
```

**Key patterns:**
- Single-file Flask app (simple, no blueprints needed)
- REST API endpoints: `/api/upload`, `/api/extract`, `/api/export`
- Frontend is vanilla HTML/CSS/JS (no frameworks)
- State managed client-side in JavaScript

## Code Style Preferences

### Swift (iOS)
- Use Swift's modern concurrency (`async/await`, not completion handlers)
- Prefer `struct` over `class` for models
- Use `@MainActor` for ViewModels
- Keep views declarative and logic-free
- Use descriptive variable names, avoid abbreviations
- Group related code with `// MARK: -` comments
- Error handling with custom `LocalizedError` enums

### Python (Web App)
- Follow PEP 8
- Use type hints where helpful but not mandatory
- Keep functions focused and single-purpose
- Use docstrings for public functions
- Prefer f-strings for formatting
- Handle errors with try/except and return JSON errors

### JavaScript (Frontend)
- Vanilla JS, no frameworks
- Use `const` and `let`, never `var`
- Use `async/await` for fetch calls
- Keep DOM manipulation simple
- Store state in module-level variables

### General
- No unnecessary comments (code should be self-documenting)
- Keep functions short and focused
- Handle errors gracefully with user-friendly messages
- Prefer simple solutions over clever ones

## Anki Export Format

The `.apkg` format is a ZIP file containing:
- `collection.anki2` - SQLite database with tables: `col`, `notes`, `cards`, `revlog`, `graves`
- `media` - JSON file mapping media filenames (empty `{}` for text-only decks)

Key schema details:
- `notes.flds`: Fields separated by `\x1f` (unit separator)
- `notes.sfld`: Sort field (usually the front of the card)
- `notes.csum`: Checksum of the sort field
- Card IDs and note IDs should be unique timestamps in milliseconds

## Claude API Integration

Both apps use the Claude API with this prompt structure:
```
Analyze the following text and extract the N most important facts...
Return ONLY a valid JSON array of flashcard objects.
Format: [{"front": "question", "back": "answer"}, ...]
```

Model: `claude-sonnet-4-20250514`
Max tokens: 4096

## Common Tasks

### Adding a new file format
1. iOS: Add parser method in `FileParserService.swift`, update `FileType` enum in `Document.swift`
2. Web: Add parser function in `app.py`, update `ALLOWED_EXTENSIONS`

### Modifying the Claude prompt
- iOS: Edit `buildPrompt()` in `ClaudeService.swift`
- Web: Edit `extract_flashcards()` in `app.py`

### Changing the Anki deck structure
- iOS: Modify `AnkiExportService.swift` (models JSON, deck JSON, SQL inserts)
- Web: Modify `create_anki_deck()` in `app.py`

## Dependencies

### iOS
- No external packages (uses only Apple frameworks)
- PDFKit, Vision, Compression, SQLite3

### Web App
- flask, anthropic, PyMuPDF, python-docx, Pillow, pytesseract, striprtf

## Running Locally

### Web App
```bash
cd webapp
./run.sh
# Opens at http://localhost:8080
```

### iOS App
Open `FileToAnki.xcodeproj` in Xcode and run on simulator or device.

## Environment

- API keys stored in iOS UserDefaults (`@AppStorage("claudeAPIKey")`)
- API keys stored in browser localStorage for web app
- No server-side storage of keys or user data
