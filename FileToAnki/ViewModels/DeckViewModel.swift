import SwiftUI
import UniformTypeIdentifiers

@MainActor
class DeckViewModel: ObservableObject {
    // State
    @Published var state: ViewState = .idle
    @Published var flashcards: [Flashcard] = []
    @Published var deckName: String = ""
    @Published var errorMessage: String?
    @Published var showingExportSheet = false
    @Published var exportedFileURL: URL?

    // Progress
    @Published var progressMessage: String = ""

    enum ViewState: Equatable {
        case idle
        case parsing
        case extracting
        case reviewing
        case exporting
        case exported
        case error
    }

    // Services
    private let fileParser = FileParserService()
    private let ankiExporter = AnkiExportService()
    private var claudeService: ClaudeService?

    // API Key
    @AppStorage("claudeAPIKey") private var apiKey: String = ""

    init() {
        updateClaudeService()
    }

    private func updateClaudeService() {
        if !apiKey.isEmpty {
            claudeService = ClaudeService(apiKey: apiKey)
        }
    }

    // MARK: - File Processing

    func processFile(url: URL) async {
        updateClaudeService()

        guard claudeService != nil else {
            errorMessage = "API key not configured"
            state = .error
            return
        }

        state = .parsing
        progressMessage = "Reading file..."

        do {
            // Parse the file
            let document = try await fileParser.parse(url: url)
            deckName = document.fileName.replacingOccurrences(of: ".\(url.pathExtension)", with: "")

            if document.textContent.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                throw FileParserService.ParserError.parsingFailed("No text content found in file")
            }

            state = .extracting
            progressMessage = "Extracting key facts with AI..."

            // Extract flashcards using Claude
            let cards = try await claudeService!.extractFlashcards(from: document.textContent)

            if cards.isEmpty {
                throw ClaudeService.ClaudeError.parsingFailed
            }

            flashcards = cards
            state = .reviewing
            progressMessage = ""

        } catch {
            errorMessage = error.localizedDescription
            state = .error
            progressMessage = ""
        }
    }

    // MARK: - Card Management

    func addCard() {
        let newCard = Flashcard(front: "New Question", back: "Answer")
        flashcards.insert(newCard, at: 0)
    }

    func deleteCard(at offsets: IndexSet) {
        flashcards.remove(atOffsets: offsets)
    }

    func updateCard(_ card: Flashcard, front: String, back: String) {
        if let index = flashcards.firstIndex(where: { $0.id == card.id }) {
            flashcards[index] = Flashcard(id: card.id, front: front, back: back)
        }
    }

    // MARK: - Export

    func exportDeck() {
        guard !flashcards.isEmpty else {
            errorMessage = "No cards to export"
            state = .error
            return
        }

        state = .exporting
        progressMessage = "Creating Anki deck..."

        let deck = AnkiDeck(name: deckName.isEmpty ? "Imported Deck" : deckName, cards: flashcards)

        do {
            let fileURL = try ankiExporter.export(deck: deck)
            exportedFileURL = fileURL
            state = .exported
            showingExportSheet = true
            progressMessage = ""
        } catch {
            errorMessage = error.localizedDescription
            state = .error
            progressMessage = ""
        }
    }

    // MARK: - Reset

    func reset() {
        state = .idle
        flashcards = []
        deckName = ""
        errorMessage = nil
        progressMessage = ""
        exportedFileURL = nil
    }
}

// MARK: - Document Picker Helper

struct DocumentPicker: UIViewControllerRepresentable {
    let onPick: (URL) -> Void

    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let supportedTypes: [UTType] = [
            .pdf,
            .plainText,
            .rtf,
            .image,
            UTType(filenameExtension: "docx") ?? .data
        ]

        let picker = UIDocumentPickerViewController(forOpeningContentTypes: supportedTypes)
        picker.delegate = context.coordinator
        picker.allowsMultipleSelection = false
        return picker
    }

    func updateUIViewController(_ uiViewController: UIDocumentPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onPick: onPick)
    }

    class Coordinator: NSObject, UIDocumentPickerDelegate {
        let onPick: (URL) -> Void

        init(onPick: @escaping (URL) -> Void) {
            self.onPick = onPick
        }

        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            guard let url = urls.first else { return }
            onPick(url)
        }
    }
}

// MARK: - Activity View for Sharing

struct ActivityView: UIViewControllerRepresentable {
    let activityItems: [Any]
    let applicationActivities: [UIActivity]? = nil

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: applicationActivities)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
