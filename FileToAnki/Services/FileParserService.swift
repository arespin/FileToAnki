import Foundation
import PDFKit
import Vision
import UniformTypeIdentifiers
import Compression

class FileParserService {
    enum ParserError: LocalizedError {
        case unsupportedFileType
        case fileNotReadable
        case parsingFailed(String)
        case ocrFailed

        var errorDescription: String? {
            switch self {
            case .unsupportedFileType:
                return "This file type is not supported"
            case .fileNotReadable:
                return "Could not read the file"
            case .parsingFailed(let reason):
                return "Failed to parse file: \(reason)"
            case .ocrFailed:
                return "Failed to extract text from image"
            }
        }
    }

    func parse(url: URL) async throws -> ParsedDocument {
        let fileType = ParsedDocument.FileType.from(url: url)

        // Start accessing security-scoped resource
        guard url.startAccessingSecurityScopedResource() else {
            throw ParserError.fileNotReadable
        }
        defer { url.stopAccessingSecurityScopedResource() }

        switch fileType {
        case .pdf:
            return try await parsePDF(url: url)
        case .txt:
            return try parsePlainText(url: url)
        case .rtf:
            return try parseRTF(url: url)
        case .docx:
            return try parseDocx(url: url)
        case .image:
            return try await parseImage(url: url)
        case .unknown:
            // Try as plain text
            return try parsePlainText(url: url)
        }
    }

    // MARK: - PDF Parsing
    private func parsePDF(url: URL) async throws -> ParsedDocument {
        guard let document = PDFDocument(url: url) else {
            throw ParserError.parsingFailed("Could not open PDF")
        }

        var fullText = ""
        for pageIndex in 0..<document.pageCount {
            if let page = document.page(at: pageIndex),
               let pageText = page.string {
                fullText += pageText + "\n\n"
            }
        }

        if fullText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            // PDF might be image-based, try OCR on first few pages
            fullText = try await ocrPDF(document: document, maxPages: 10)
        }

        return ParsedDocument(
            fileName: url.lastPathComponent,
            fileType: .pdf,
            textContent: fullText,
            pageCount: document.pageCount
        )
    }

    private func ocrPDF(document: PDFDocument, maxPages: Int) async throws -> String {
        var fullText = ""
        let pagesToProcess = min(document.pageCount, maxPages)

        for pageIndex in 0..<pagesToProcess {
            guard let page = document.page(at: pageIndex) else { continue }

            let pageRect = page.bounds(for: .mediaBox)
            let renderer = UIGraphicsImageRenderer(size: pageRect.size)
            let image = renderer.image { ctx in
                UIColor.white.set()
                ctx.fill(pageRect)
                ctx.cgContext.translateBy(x: 0, y: pageRect.size.height)
                ctx.cgContext.scaleBy(x: 1.0, y: -1.0)
                page.draw(with: .mediaBox, to: ctx.cgContext)
            }

            if let pageText = try await performOCR(on: image) {
                fullText += pageText + "\n\n"
            }
        }

        return fullText
    }

    // MARK: - Plain Text Parsing
    private func parsePlainText(url: URL) throws -> ParsedDocument {
        let content = try String(contentsOf: url, encoding: .utf8)

        return ParsedDocument(
            fileName: url.lastPathComponent,
            fileType: .txt,
            textContent: content,
            pageCount: nil
        )
    }

    // MARK: - RTF Parsing
    private func parseRTF(url: URL) throws -> ParsedDocument {
        let data = try Data(contentsOf: url)

        guard let attributedString = try? NSAttributedString(
            data: data,
            options: [.documentType: NSAttributedString.DocumentType.rtf],
            documentAttributes: nil
        ) else {
            throw ParserError.parsingFailed("Could not parse RTF content")
        }

        return ParsedDocument(
            fileName: url.lastPathComponent,
            fileType: .rtf,
            textContent: attributedString.string,
            pageCount: nil
        )
    }

    // MARK: - DOCX Parsing
    private func parseDocx(url: URL) throws -> ParsedDocument {
        // DOCX is a ZIP file containing XML
        let fileManager = FileManager.default
        let tempDir = fileManager.temporaryDirectory.appendingPathComponent(UUID().uuidString)

        do {
            try fileManager.createDirectory(at: tempDir, withIntermediateDirectories: true)
            defer { try? fileManager.removeItem(at: tempDir) }

            // Unzip the docx file
            try unzipFile(at: url, to: tempDir)

            // Read the main document content
            let documentXML = tempDir.appendingPathComponent("word/document.xml")

            guard fileManager.fileExists(atPath: documentXML.path) else {
                throw ParserError.parsingFailed("Invalid DOCX structure")
            }

            let xmlData = try Data(contentsOf: documentXML)
            let text = extractTextFromDocxXML(data: xmlData)

            return ParsedDocument(
                fileName: url.lastPathComponent,
                fileType: .docx,
                textContent: text,
                pageCount: nil
            )
        } catch let error as ParserError {
            throw error
        } catch {
            throw ParserError.parsingFailed(error.localizedDescription)
        }
    }

    private func unzipFile(at sourceURL: URL, to destinationURL: URL) throws {
        let fileManager = FileManager.default
        let zipData = try Data(contentsOf: sourceURL)

        // Find and extract files from ZIP
        var offset = 0

        while offset < zipData.count - 4 {
            // Check for local file header signature (0x04034b50)
            let sig = zipData.subdata(in: offset..<offset+4)
            guard sig == Data([0x50, 0x4B, 0x03, 0x04]) else {
                break
            }

            // Parse local file header
            let compressedSize = zipData.subdata(in: offset+18..<offset+22).withUnsafeBytes { $0.load(as: UInt32.self) }
            let uncompressedSize = zipData.subdata(in: offset+22..<offset+26).withUnsafeBytes { $0.load(as: UInt32.self) }
            let fileNameLength = zipData.subdata(in: offset+26..<offset+28).withUnsafeBytes { $0.load(as: UInt16.self) }
            let extraFieldLength = zipData.subdata(in: offset+28..<offset+30).withUnsafeBytes { $0.load(as: UInt16.self) }
            let compressionMethod = zipData.subdata(in: offset+8..<offset+10).withUnsafeBytes { $0.load(as: UInt16.self) }

            let headerEnd = offset + 30
            let fileNameData = zipData.subdata(in: headerEnd..<headerEnd+Int(fileNameLength))
            guard let fileName = String(data: fileNameData, encoding: .utf8) else {
                offset = headerEnd + Int(fileNameLength) + Int(extraFieldLength) + Int(compressedSize)
                continue
            }

            let dataStart = headerEnd + Int(fileNameLength) + Int(extraFieldLength)
            let dataEnd = dataStart + Int(compressedSize)

            // Skip directories
            if !fileName.hasSuffix("/") {
                let fileData: Data
                if compressionMethod == 0 {
                    // Stored (no compression)
                    fileData = zipData.subdata(in: dataStart..<dataEnd)
                } else if compressionMethod == 8 {
                    // Deflate compression
                    let compressedData = zipData.subdata(in: dataStart..<dataEnd)
                    guard let decompressed = decompressDeflate(compressedData, uncompressedSize: Int(uncompressedSize)) else {
                        offset = dataEnd
                        continue
                    }
                    fileData = decompressed
                } else {
                    offset = dataEnd
                    continue
                }

                let filePath = destinationURL.appendingPathComponent(fileName)
                let fileDir = filePath.deletingLastPathComponent()

                try fileManager.createDirectory(at: fileDir, withIntermediateDirectories: true)
                try fileData.write(to: filePath)
            }

            offset = dataEnd
        }
    }

    private func decompressDeflate(_ data: Data, uncompressedSize: Int) -> Data? {
        // Use Apple's Compression framework for deflate decompression
        var destinationBuffer = Data(count: uncompressedSize)

        let decodedSize = destinationBuffer.withUnsafeMutableBytes { destPtr -> Int in
            data.withUnsafeBytes { sourcePtr -> Int in
                guard let destBase = destPtr.baseAddress?.assumingMemoryBound(to: UInt8.self),
                      let sourceBase = sourcePtr.baseAddress?.assumingMemoryBound(to: UInt8.self) else {
                    return 0
                }
                return compression_decode_buffer(
                    destBase,
                    uncompressedSize,
                    sourceBase,
                    data.count,
                    nil,
                    COMPRESSION_ZLIB
                )
            }
        }

        guard decodedSize > 0 else { return nil }
        return destinationBuffer.prefix(decodedSize)
    }

    private func extractTextFromDocxXML(data: Data) -> String {
        // Simple XML parsing to extract text from <w:t> tags
        guard let xmlString = String(data: data, encoding: .utf8) else {
            return ""
        }

        var result = ""
        var inTextTag = false
        var currentText = ""

        let scanner = Scanner(string: xmlString)
        scanner.charactersToBeSkipped = nil

        while !scanner.isAtEnd {
            if let _ = scanner.scanString("<w:t") {
                // Skip attributes until >
                _ = scanner.scanUpToString(">")
                _ = scanner.scanString(">")
                inTextTag = true
                currentText = ""
            } else if let _ = scanner.scanString("</w:t>") {
                if inTextTag {
                    result += currentText
                }
                inTextTag = false
            } else if let _ = scanner.scanString("<w:p") {
                // New paragraph
                if !result.isEmpty && !result.hasSuffix("\n") {
                    result += "\n"
                }
                _ = scanner.scanUpToString(">")
                _ = scanner.scanString(">")
            } else if let _ = scanner.scanString("<") {
                // Skip other tags
                _ = scanner.scanUpToString(">")
                _ = scanner.scanString(">")
            } else if let char = scanner.scanCharacter() {
                if inTextTag {
                    currentText.append(char)
                }
            }
        }

        return result
    }

    // MARK: - Image Parsing (OCR)
    private func parseImage(url: URL) async throws -> ParsedDocument {
        guard let imageData = try? Data(contentsOf: url),
              let image = UIImage(data: imageData) else {
            throw ParserError.fileNotReadable
        }

        guard let text = try await performOCR(on: image) else {
            throw ParserError.ocrFailed
        }

        return ParsedDocument(
            fileName: url.lastPathComponent,
            fileType: .image,
            textContent: text,
            pageCount: nil
        )
    }

    private func performOCR(on image: UIImage) async throws -> String? {
        guard let cgImage = image.cgImage else {
            return nil
        }

        return try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                guard let observations = request.results as? [VNRecognizedTextObservation] else {
                    continuation.resume(returning: nil)
                    return
                }

                let text = observations.compactMap { observation in
                    observation.topCandidates(1).first?.string
                }.joined(separator: "\n")

                continuation.resume(returning: text)
            }

            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }
}
