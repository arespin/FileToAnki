import Foundation

struct ParsedDocument {
    let fileName: String
    let fileType: FileType
    let textContent: String
    let pageCount: Int?

    enum FileType: String {
        case pdf = "PDF"
        case txt = "Text"
        case rtf = "RTF"
        case docx = "Word"
        case image = "Image"
        case unknown = "Unknown"

        static func from(url: URL) -> FileType {
            switch url.pathExtension.lowercased() {
            case "pdf":
                return .pdf
            case "txt", "text":
                return .txt
            case "rtf":
                return .rtf
            case "docx", "doc":
                return .docx
            case "jpg", "jpeg", "png", "heic", "tiff", "bmp", "gif":
                return .image
            default:
                return .unknown
            }
        }
    }
}
