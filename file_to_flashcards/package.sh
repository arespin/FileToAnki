#!/bin/bash
# Package FileToFlashcards add-on for distribution

cd "$(dirname "$0")/.."

# Clean up pycache
find file_to_flashcards -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Create the package
zip -r file_to_flashcards.ankiaddon file_to_flashcards -x "*.pyc" -x "*__pycache__*" -x "*.sh"

echo "Created file_to_flashcards.ankiaddon"
echo "Install in Anki via: Tools -> Add-ons -> Install from file"
