import Foundation

class ClaudeService {
    private let apiKey: String
    private let baseURL = "https://api.anthropic.com/v1/messages"

    enum ClaudeError: LocalizedError {
        case invalidAPIKey
        case networkError(String)
        case invalidResponse
        case rateLimited
        case parsingFailed

        var errorDescription: String? {
            switch self {
            case .invalidAPIKey:
                return "Invalid API key. Please check your Claude API key."
            case .networkError(let message):
                return "Network error: \(message)"
            case .invalidResponse:
                return "Received an invalid response from Claude"
            case .rateLimited:
                return "Rate limited. Please try again later."
            case .parsingFailed:
                return "Failed to parse flashcards from response"
            }
        }
    }

    init(apiKey: String) {
        self.apiKey = apiKey
    }

    func extractFlashcards(from text: String, maxCards: Int = 25) async throws -> [Flashcard] {
        let prompt = buildPrompt(text: text, maxCards: maxCards)

        let requestBody: [String: Any] = [
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [
                ["role": "user", "content": prompt]
            ]
        ]

        var request = URLRequest(url: URL(string: baseURL)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "x-api-key")
        request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ClaudeError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200:
            return try parseFlashcardsFromResponse(data: data)
        case 401:
            throw ClaudeError.invalidAPIKey
        case 429:
            throw ClaudeError.rateLimited
        default:
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw ClaudeError.networkError("Status \(httpResponse.statusCode): \(errorMessage)")
        }
    }

    private func buildPrompt(text: String, maxCards: Int) -> String {
        // Truncate text if too long (Claude has context limits)
        let maxTextLength = 50000
        let truncatedText = text.count > maxTextLength
            ? String(text.prefix(maxTextLength)) + "\n[Text truncated...]"
            : text

        return """
        Analyze the following text and extract the \(maxCards) most important facts, concepts, and pieces of information worth memorizing.

        For each fact, create a flashcard with:
        - "front": A clear, specific question or prompt
        - "back": A concise, accurate answer

        Guidelines:
        - Focus on key concepts, definitions, important facts, dates, formulas, and relationships
        - Questions should be specific and unambiguous
        - Answers should be concise but complete
        - Avoid trivial or obvious information
        - Each card should test ONE concept

        Return ONLY a valid JSON array of flashcard objects. No other text or explanation.
        Format: [{"front": "question", "back": "answer"}, ...]

        TEXT TO ANALYZE:
        ---
        \(truncatedText)
        ---

        JSON flashcards:
        """
    }

    private func parseFlashcardsFromResponse(data: Data) throws -> [Flashcard] {
        // Parse Claude's response structure
        struct ClaudeResponse: Decodable {
            struct Content: Decodable {
                let type: String
                let text: String?
            }
            let content: [Content]
        }

        let response = try JSONDecoder().decode(ClaudeResponse.self, from: data)

        guard let textContent = response.content.first(where: { $0.type == "text" }),
              let text = textContent.text else {
            throw ClaudeError.parsingFailed
        }

        // Extract JSON array from the response
        let jsonText = extractJSON(from: text)

        guard let jsonData = jsonText.data(using: .utf8) else {
            throw ClaudeError.parsingFailed
        }

        do {
            let flashcards = try JSONDecoder().decode([Flashcard].self, from: jsonData)
            return flashcards
        } catch {
            throw ClaudeError.parsingFailed
        }
    }

    private func extractJSON(from text: String) -> String {
        // Find JSON array in the response
        var result = text.trimmingCharacters(in: .whitespacesAndNewlines)

        // Remove markdown code blocks if present
        if result.hasPrefix("```json") {
            result = String(result.dropFirst(7))
        } else if result.hasPrefix("```") {
            result = String(result.dropFirst(3))
        }

        if result.hasSuffix("```") {
            result = String(result.dropLast(3))
        }

        result = result.trimmingCharacters(in: .whitespacesAndNewlines)

        // Find the array bounds
        if let startIndex = result.firstIndex(of: "["),
           let endIndex = result.lastIndex(of: "]") {
            result = String(result[startIndex...endIndex])
        }

        return result
    }
}
