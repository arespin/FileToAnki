"""
Main dialog and workflow for FileToFlashcards.
"""

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QLineEdit, QListWidget,
    QProgressBar, QFileDialog, QMessageBox, QListWidgetItem,
    QCheckBox, QWidget, QGroupBox, Qt, QThread, pyqtSignal,
    QAbstractItemView
)

from .file_parser import parse_file, get_file_filter, get_missing_dependencies
from .claude_service import extract_flashcards, ANTHROPIC_AVAILABLE
from .card_creator import get_deck_names, create_cards

# Qt compatibility for PyQt5/PyQt6
try:
    ECHO_PASSWORD = QLineEdit.EchoMode.Password
    ECHO_NORMAL = QLineEdit.EchoMode.Normal
    NO_SELECTION = QAbstractItemView.SelectionMode.NoSelection
except AttributeError:
    ECHO_PASSWORD = QLineEdit.Password
    ECHO_NORMAL = QLineEdit.Normal
    NO_SELECTION = QAbstractItemView.NoSelection


class ExtractWorker(QThread):
    """Background thread for file parsing and Claude API calls."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, file_path, api_key, max_cards):
        super().__init__()
        self.file_path = file_path
        self.api_key = api_key
        self.max_cards = max_cards

    def run(self):
        try:
            self.progress.emit("Parsing file...")
            text = parse_file(self.file_path)

            if not text.strip():
                self.error.emit("No text content found in file")
                return

            self.progress.emit("Extracting flashcards with Claude...")
            flashcards = extract_flashcards(text, self.api_key, self.max_cards)

            if not flashcards:
                self.error.emit("No flashcards generated")
                return

            self.finished.emit(flashcards)

        except Exception as e:
            self.error.emit(str(e))


class FlashcardItem(QWidget):
    """Custom widget for displaying a flashcard in the list."""

    def __init__(self, index, front, back, parent=None):
        super().__init__(parent)
        self.index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox)

        text_layout = QVBoxLayout()
        self.front_label = QLabel(f"Q: {front[:100]}{'...' if len(front) > 100 else ''}")
        self.front_label.setWordWrap(True)
        self.back_label = QLabel(f"A: {back[:100]}{'...' if len(back) > 100 else ''}")
        self.back_label.setWordWrap(True)
        self.back_label.setStyleSheet("color: gray;")
        text_layout.addWidget(self.front_label)
        text_layout.addWidget(self.back_label)
        layout.addLayout(text_layout, 1)


class FileToFlashcardsDialog(QDialog):
    """Main dialog for the FileToFlashcards add-on."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FileToFlashcards")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self.flashcards = []
        self.file_path = None
        self.worker = None

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # API Key section
        api_group = QGroupBox("Claude API")
        api_layout = QHBoxLayout(api_group)
        api_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(ECHO_PASSWORD)
        self.api_key_input.setPlaceholderText("sk-ant-...")
        api_layout.addWidget(self.api_key_input, 1)
        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self.toggle_api_key_visibility)
        api_layout.addWidget(self.show_key_btn)
        layout.addWidget(api_group)

        # File selection
        file_group = QGroupBox("File")
        file_layout = QHBoxLayout(file_group)
        self.file_label = QLabel("No file selected")
        file_layout.addWidget(self.file_label, 1)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        layout.addWidget(file_group)

        # Settings
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout(settings_group)

        settings_layout.addWidget(QLabel("Deck:"))
        self.deck_combo = QComboBox()
        self.deck_combo.addItems(get_deck_names())
        settings_layout.addWidget(self.deck_combo, 1)

        settings_layout.addWidget(QLabel("Max Cards:"))
        self.max_cards_spin = QSpinBox()
        self.max_cards_spin.setRange(5, 50)
        self.max_cards_spin.setValue(25)
        settings_layout.addWidget(self.max_cards_spin)

        layout.addWidget(settings_group)

        # Generate button
        self.generate_btn = QPushButton("Generate Flashcards")
        self.generate_btn.clicked.connect(self.generate_flashcards)
        self.generate_btn.setStyleSheet("padding: 10px; font-weight: bold;")
        layout.addWidget(self.generate_btn)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # Preview list
        preview_group = QGroupBox("Generated Flashcards")
        preview_layout = QVBoxLayout(preview_group)

        self.card_list = QListWidget()
        self.card_list.setSelectionMode(NO_SELECTION)
        preview_layout.addWidget(self.card_list)

        # Select all / none buttons
        select_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_cards)
        select_layout.addWidget(self.select_all_btn)
        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self.select_no_cards)
        select_layout.addWidget(self.select_none_btn)
        select_layout.addStretch()
        preview_layout.addLayout(select_layout)

        layout.addWidget(preview_group, 1)

        # Bottom buttons
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        self.import_btn = QPushButton("Import to Anki")
        self.import_btn.clicked.connect(self.import_cards)
        self.import_btn.setEnabled(False)
        self.import_btn.setStyleSheet("padding: 10px; font-weight: bold;")
        button_layout.addWidget(self.import_btn)
        layout.addLayout(button_layout)

        # Check dependencies
        self.check_dependencies()

    def check_dependencies(self):
        """Show warnings for missing dependencies."""
        warnings = []

        if not ANTHROPIC_AVAILABLE:
            warnings.append("anthropic package not installed (required)")

        missing = get_missing_dependencies()
        if missing:
            warnings.extend(missing)

        if warnings:
            msg = "Missing dependencies:\n\n" + "\n".join(f"- {w}" for w in warnings)
            msg += "\n\nSome features may not be available."
            QMessageBox.warning(self, "Missing Dependencies", msg)

    def load_config(self):
        """Load saved configuration."""
        config = mw.addonManager.getConfig(__name__.split('.')[0])
        if config:
            self.api_key_input.setText(config.get('api_key', ''))
            default_deck = config.get('default_deck', 'Default')
            index = self.deck_combo.findText(default_deck)
            if index >= 0:
                self.deck_combo.setCurrentIndex(index)
            self.max_cards_spin.setValue(config.get('max_cards', 25))

    def save_config(self):
        """Save configuration."""
        config = {
            'api_key': self.api_key_input.text(),
            'default_deck': self.deck_combo.currentText(),
            'max_cards': self.max_cards_spin.value()
        }
        mw.addonManager.writeConfig(__name__.split('.')[0], config)

    def toggle_api_key_visibility(self, show):
        """Toggle API key visibility."""
        if show:
            self.api_key_input.setEchoMode(ECHO_NORMAL)
            self.show_key_btn.setText("Hide")
        else:
            self.api_key_input.setEchoMode(ECHO_PASSWORD)
            self.show_key_btn.setText("Show")

    def browse_file(self):
        """Open file browser."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            get_file_filter()
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(file_path.split('/')[-1])

    def generate_flashcards(self):
        """Start flashcard generation."""
        if not self.file_path:
            QMessageBox.warning(self, "Error", "Please select a file first")
            return

        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter your Claude API key")
            return

        if not ANTHROPIC_AVAILABLE:
            QMessageBox.critical(
                self, "Error",
                "The anthropic package is not installed.\n"
                "Please install it with: pip install anthropic"
            )
            return

        # Save config
        self.save_config()

        # Clear previous results
        self.card_list.clear()
        self.flashcards = []
        self.import_btn.setEnabled(False)

        # Show progress
        self.progress_bar.show()
        self.status_label.show()
        self.generate_btn.setEnabled(False)

        # Start worker thread
        self.worker = ExtractWorker(
            self.file_path,
            api_key,
            self.max_cards_spin.value()
        )
        self.worker.finished.connect(self.on_extraction_finished)
        self.worker.error.connect(self.on_extraction_error)
        self.worker.progress.connect(self.on_progress_update)
        self.worker.start()

    def on_progress_update(self, message):
        """Update status label."""
        self.status_label.setText(message)

    def on_extraction_finished(self, flashcards):
        """Handle successful extraction."""
        self.progress_bar.hide()
        self.status_label.hide()
        self.generate_btn.setEnabled(True)

        self.flashcards = flashcards
        self.populate_card_list()
        self.import_btn.setEnabled(True)

        QMessageBox.information(
            self, "Success",
            f"Generated {len(flashcards)} flashcards.\n"
            "Review them below and click 'Import to Anki' to add them."
        )

    def on_extraction_error(self, error_message):
        """Handle extraction error."""
        self.progress_bar.hide()
        self.status_label.hide()
        self.generate_btn.setEnabled(True)

        QMessageBox.critical(self, "Error", f"Failed to generate flashcards:\n\n{error_message}")

    def populate_card_list(self):
        """Populate the card list with generated flashcards."""
        self.card_list.clear()

        for i, card in enumerate(self.flashcards):
            item = QListWidgetItem(self.card_list)
            widget = FlashcardItem(i, card['front'], card['back'])
            item.setSizeHint(widget.sizeHint())
            self.card_list.addItem(item)
            self.card_list.setItemWidget(item, widget)

    def select_all_cards(self):
        """Select all cards."""
        for i in range(self.card_list.count()):
            item = self.card_list.item(i)
            widget = self.card_list.itemWidget(item)
            if widget:
                widget.checkbox.setChecked(True)

    def select_no_cards(self):
        """Deselect all cards."""
        for i in range(self.card_list.count()):
            item = self.card_list.item(i)
            widget = self.card_list.itemWidget(item)
            if widget:
                widget.checkbox.setChecked(False)

    def get_selected_cards(self):
        """Return list of selected flashcards."""
        selected = []
        for i in range(self.card_list.count()):
            item = self.card_list.item(i)
            widget = self.card_list.itemWidget(item)
            if widget and widget.checkbox.isChecked():
                selected.append(self.flashcards[i])
        return selected

    def import_cards(self):
        """Import selected cards to Anki."""
        selected = self.get_selected_cards()

        if not selected:
            QMessageBox.warning(self, "Error", "No cards selected for import")
            return

        deck_name = self.deck_combo.currentText()

        try:
            count = create_cards(selected, deck_name)
            QMessageBox.information(
                self, "Success",
                f"Successfully imported {count} cards to deck '{deck_name}'!"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import cards:\n\n{str(e)}")


def show_dialog():
    """Show the FileToFlashcards dialog."""
    dialog = FileToFlashcardsDialog(mw)
    dialog.exec()
