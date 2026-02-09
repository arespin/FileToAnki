import Foundation

struct AnkiDeck {
    let id: Int64
    let name: String
    let cards: [Flashcard]
    let createdAt: Date

    init(name: String, cards: [Flashcard]) {
        self.id = Int64(Date().timeIntervalSince1970 * 1000)
        self.name = name
        self.cards = cards
        self.createdAt = Date()
    }

    var sanitizedName: String {
        let invalidChars = CharacterSet(charactersIn: "/\\:*?\"<>|")
        return name.components(separatedBy: invalidChars).joined(separator: "_")
    }
}
