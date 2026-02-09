import Foundation

struct Flashcard: Identifiable, Codable, Equatable {
    let id: UUID
    var front: String
    var back: String

    init(id: UUID = UUID(), front: String, back: String) {
        self.id = id
        self.front = front
        self.back = back
    }

    // For decoding from Claude API response
    enum CodingKeys: String, CodingKey {
        case front
        case back
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = UUID()
        self.front = try container.decode(String.self, forKey: .front)
        self.back = try container.decode(String.self, forKey: .back)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(front, forKey: .front)
        try container.encode(back, forKey: .back)
    }
}
