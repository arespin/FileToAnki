import Foundation
import SQLite3

class AnkiExportService {
    enum ExportError: LocalizedError {
        case databaseCreationFailed
        case writeFailed(String)
        case zipFailed

        var errorDescription: String? {
            switch self {
            case .databaseCreationFailed:
                return "Failed to create Anki database"
            case .writeFailed(let reason):
                return "Failed to write deck: \(reason)"
            case .zipFailed:
                return "Failed to create .apkg file"
            }
        }
    }

    private let fileManager = FileManager.default

    func export(deck: AnkiDeck) throws -> URL {
        let tempDir = fileManager.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try fileManager.createDirectory(at: tempDir, withIntermediateDirectories: true)

        let dbPath = tempDir.appendingPathComponent("collection.anki2")
        let mediaPath = tempDir.appendingPathComponent("media")

        // Create the SQLite database
        try createAnkiDatabase(at: dbPath, deck: deck)

        // Create empty media file (required by Anki)
        try "{}".write(to: mediaPath, atomically: true, encoding: .utf8)

        // Create the .apkg file (zip)
        let outputDir = fileManager.temporaryDirectory
        let apkgPath = outputDir.appendingPathComponent("\(deck.sanitizedName).apkg")

        // Remove existing file if present
        try? fileManager.removeItem(at: apkgPath)

        // Create zip archive using native implementation
        try createZipArchive(from: tempDir, to: apkgPath)

        // Cleanup temp directory
        try? fileManager.removeItem(at: tempDir)

        return apkgPath
    }

    private func createZipArchive(from sourceDir: URL, to destinationURL: URL) throws {
        // Get list of files to include
        let contents = try fileManager.contentsOfDirectory(at: sourceDir, includingPropertiesForKeys: nil)

        var zipData = Data()

        // ZIP file signature and structure
        var centralDirectory = Data()
        var localHeaderOffset: UInt32 = 0

        for fileURL in contents {
            let fileName = fileURL.lastPathComponent
            let fileData = try Data(contentsOf: fileURL)

            // Local file header
            var localHeader = Data()

            // Signature
            localHeader.append(contentsOf: [0x50, 0x4B, 0x03, 0x04])
            // Version needed (2.0)
            localHeader.append(contentsOf: [0x14, 0x00])
            // General purpose bit flag
            localHeader.append(contentsOf: [0x00, 0x00])
            // Compression method (0 = stored, no compression)
            localHeader.append(contentsOf: [0x00, 0x00])
            // Last mod time
            localHeader.append(contentsOf: [0x00, 0x00])
            // Last mod date
            localHeader.append(contentsOf: [0x00, 0x00])
            // CRC-32
            let crc = crc32(fileData)
            localHeader.append(contentsOf: withUnsafeBytes(of: crc.littleEndian) { Array($0) })
            // Compressed size
            let size = UInt32(fileData.count)
            localHeader.append(contentsOf: withUnsafeBytes(of: size.littleEndian) { Array($0) })
            // Uncompressed size
            localHeader.append(contentsOf: withUnsafeBytes(of: size.littleEndian) { Array($0) })
            // File name length
            let fileNameData = fileName.data(using: .utf8)!
            let fileNameLength = UInt16(fileNameData.count)
            localHeader.append(contentsOf: withUnsafeBytes(of: fileNameLength.littleEndian) { Array($0) })
            // Extra field length
            localHeader.append(contentsOf: [0x00, 0x00])
            // File name
            localHeader.append(fileNameData)

            // Central directory header
            var cdHeader = Data()
            // Signature
            cdHeader.append(contentsOf: [0x50, 0x4B, 0x01, 0x02])
            // Version made by
            cdHeader.append(contentsOf: [0x14, 0x00])
            // Version needed
            cdHeader.append(contentsOf: [0x14, 0x00])
            // General purpose bit flag
            cdHeader.append(contentsOf: [0x00, 0x00])
            // Compression method
            cdHeader.append(contentsOf: [0x00, 0x00])
            // Last mod time
            cdHeader.append(contentsOf: [0x00, 0x00])
            // Last mod date
            cdHeader.append(contentsOf: [0x00, 0x00])
            // CRC-32
            cdHeader.append(contentsOf: withUnsafeBytes(of: crc.littleEndian) { Array($0) })
            // Compressed size
            cdHeader.append(contentsOf: withUnsafeBytes(of: size.littleEndian) { Array($0) })
            // Uncompressed size
            cdHeader.append(contentsOf: withUnsafeBytes(of: size.littleEndian) { Array($0) })
            // File name length
            cdHeader.append(contentsOf: withUnsafeBytes(of: fileNameLength.littleEndian) { Array($0) })
            // Extra field length
            cdHeader.append(contentsOf: [0x00, 0x00])
            // File comment length
            cdHeader.append(contentsOf: [0x00, 0x00])
            // Disk number start
            cdHeader.append(contentsOf: [0x00, 0x00])
            // Internal file attributes
            cdHeader.append(contentsOf: [0x00, 0x00])
            // External file attributes
            cdHeader.append(contentsOf: [0x00, 0x00, 0x00, 0x00])
            // Relative offset of local header
            cdHeader.append(contentsOf: withUnsafeBytes(of: localHeaderOffset.littleEndian) { Array($0) })
            // File name
            cdHeader.append(fileNameData)

            centralDirectory.append(cdHeader)

            zipData.append(localHeader)
            zipData.append(fileData)

            localHeaderOffset = UInt32(zipData.count)
        }

        let centralDirOffset = UInt32(zipData.count)
        let centralDirSize = UInt32(centralDirectory.count)
        let numEntries = UInt16(contents.count)

        zipData.append(centralDirectory)

        // End of central directory record
        var eocd = Data()
        // Signature
        eocd.append(contentsOf: [0x50, 0x4B, 0x05, 0x06])
        // Number of this disk
        eocd.append(contentsOf: [0x00, 0x00])
        // Disk where central directory starts
        eocd.append(contentsOf: [0x00, 0x00])
        // Number of central directory records on this disk
        eocd.append(contentsOf: withUnsafeBytes(of: numEntries.littleEndian) { Array($0) })
        // Total number of central directory records
        eocd.append(contentsOf: withUnsafeBytes(of: numEntries.littleEndian) { Array($0) })
        // Size of central directory
        eocd.append(contentsOf: withUnsafeBytes(of: centralDirSize.littleEndian) { Array($0) })
        // Offset of central directory
        eocd.append(contentsOf: withUnsafeBytes(of: centralDirOffset.littleEndian) { Array($0) })
        // Comment length
        eocd.append(contentsOf: [0x00, 0x00])

        zipData.append(eocd)

        try zipData.write(to: destinationURL)
    }

    private func crc32(_ data: Data) -> UInt32 {
        var crc: UInt32 = 0xFFFFFFFF

        let table: [UInt32] = (0..<256).map { i -> UInt32 in
            var c = UInt32(i)
            for _ in 0..<8 {
                if c & 1 != 0 {
                    c = 0xEDB88320 ^ (c >> 1)
                } else {
                    c = c >> 1
                }
            }
            return c
        }

        for byte in data {
            let index = Int((crc ^ UInt32(byte)) & 0xFF)
            crc = table[index] ^ (crc >> 8)
        }

        return crc ^ 0xFFFFFFFF
    }

    private func createAnkiDatabase(at url: URL, deck: AnkiDeck) throws {
        var db: OpaquePointer?

        guard sqlite3_open(url.path, &db) == SQLITE_OK else {
            throw ExportError.databaseCreationFailed
        }
        defer { sqlite3_close(db) }

        // Create tables
        try executeSQL(db: db, sql: createTablesSQL)

        // Insert collection data
        let modelId = deck.id + 1
        let now = Int64(Date().timeIntervalSince1970)

        let modelsJSON = createModelsJSON(modelId: modelId)
        let decksJSON = createDecksJSON(deckId: deck.id, deckName: deck.name)
        let dconfJSON = createDconfJSON()

        let colSQL = """
        INSERT INTO col VALUES(1, \(now), \(now * 1000), \(now * 1000), 11, 0, 0, 0, '\(escapeSQL(confJSON))', '\(escapeSQL(modelsJSON))', '\(escapeSQL(decksJSON))', '\(escapeSQL(dconfJSON))', '{}');
        """
        try executeSQL(db: db, sql: colSQL)

        // Insert notes and cards
        for (index, card) in deck.cards.enumerated() {
            let noteId = deck.id + Int64(index) + 100
            let cardId = deck.id + Int64(index) + 1000
            let guid = generateGuid()
            let sfld = card.front
            let flds = "\(card.front)\u{1f}\(card.back)"
            let csum = checksum(sfld)

            let noteSQL = """
            INSERT INTO notes VALUES(\(noteId), '\(guid)', \(modelId), \(now), -1, '', '\(escapeSQL(flds))', '\(escapeSQL(sfld))', \(csum), 0, '');
            """
            try executeSQL(db: db, sql: noteSQL)

            let cardSQL = """
            INSERT INTO cards VALUES(\(cardId), \(noteId), \(deck.id), 0, \(now), -1, 0, 0, \(index), 0, 0, 0, 0, 0, 0, 0, 0, '');
            """
            try executeSQL(db: db, sql: cardSQL)
        }
    }

    private func executeSQL(db: OpaquePointer?, sql: String) throws {
        var errMsg: UnsafeMutablePointer<CChar>?
        if sqlite3_exec(db, sql, nil, nil, &errMsg) != SQLITE_OK {
            let error = errMsg.map { String(cString: $0) } ?? "Unknown error"
            sqlite3_free(errMsg)
            throw ExportError.writeFailed(error)
        }
    }

    private func escapeSQL(_ string: String) -> String {
        return string.replacingOccurrences(of: "'", with: "''")
    }

    private func generateGuid() -> String {
        let chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return String((0..<10).map { _ in chars.randomElement()! })
    }

    private func checksum(_ string: String) -> Int64 {
        var hash: UInt32 = 0
        for byte in string.utf8 {
            hash = hash &* 31 &+ UInt32(byte)
        }
        return Int64(hash & 0xFFFFFFFF)
    }

    private let createTablesSQL = """
    CREATE TABLE IF NOT EXISTS col (
        id integer primary key,
        crt integer not null,
        mod integer not null,
        scm integer not null,
        ver integer not null,
        dty integer not null,
        usn integer not null,
        ls integer not null,
        conf text not null,
        models text not null,
        decks text not null,
        dconf text not null,
        tags text not null
    );
    CREATE TABLE IF NOT EXISTS notes (
        id integer primary key,
        guid text not null,
        mid integer not null,
        mod integer not null,
        usn integer not null,
        tags text not null,
        flds text not null,
        sfld integer not null,
        csum integer not null,
        flags integer not null,
        data text not null
    );
    CREATE TABLE IF NOT EXISTS cards (
        id integer primary key,
        nid integer not null,
        did integer not null,
        ord integer not null,
        mod integer not null,
        usn integer not null,
        type integer not null,
        queue integer not null,
        due integer not null,
        ivl integer not null,
        factor integer not null,
        reps integer not null,
        lapses integer not null,
        left integer not null,
        odue integer not null,
        odid integer not null,
        flags integer not null,
        data text not null
    );
    CREATE TABLE IF NOT EXISTS revlog (
        id integer primary key,
        cid integer not null,
        usn integer not null,
        ease integer not null,
        ivl integer not null,
        lastIvl integer not null,
        factor integer not null,
        time integer not null,
        type integer not null
    );
    CREATE TABLE IF NOT EXISTS graves (
        usn integer not null,
        oid integer not null,
        type integer not null
    );
    CREATE INDEX IF NOT EXISTS ix_notes_usn on notes (usn);
    CREATE INDEX IF NOT EXISTS ix_cards_usn on cards (usn);
    CREATE INDEX IF NOT EXISTS ix_revlog_usn on revlog (usn);
    CREATE INDEX IF NOT EXISTS ix_cards_nid on cards (nid);
    CREATE INDEX IF NOT EXISTS ix_cards_sched on cards (did, queue, due);
    CREATE INDEX IF NOT EXISTS ix_revlog_cid on revlog (cid);
    CREATE INDEX IF NOT EXISTS ix_notes_csum on notes (csum);
    """

    private let confJSON = """
    {"activeDecks":[1],"curDeck":1,"newSpread":0,"collapseTime":1200,"timeLim":0,"estTimes":true,"dueCounts":true,"curModel":null,"nextPos":1,"sortType":"noteFld","sortBackwards":false,"addToCur":true}
    """

    private func createModelsJSON(modelId: Int64) -> String {
        let now = Int64(Date().timeIntervalSince1970 * 1000)
        return """
        {"\(modelId)":{"id":\(modelId),"name":"Basic","type":0,"mod":\(now),"usn":-1,"sortf":0,"did":1,"tmpls":[{"name":"Card 1","ord":0,"qfmt":"{{Front}}","afmt":"{{FrontSide}}<hr id=answer>{{Back}}","bqfmt":"","bafmt":"","did":null,"bfont":"","bsize":0}],"flds":[{"name":"Front","ord":0,"sticky":false,"rtl":false,"font":"Arial","size":20,"media":[]},{"name":"Back","ord":1,"sticky":false,"rtl":false,"font":"Arial","size":20,"media":[]}],"css":".card {font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white;}","latexPre":"\\\\documentclass[12pt]{article}\\n\\\\special{papersize=3in,5in}\\n\\\\usepackage[utf8]{inputenc}\\n\\\\usepackage{amssymb,amsmath}\\n\\\\pagestyle{empty}\\n\\\\setlength{\\\\parindent}{0in}\\n\\\\begin{document}\\n","latexPost":"\\n\\\\end{document}","latexsvg":false,"req":[[0,"any",[0]]]}}
        """
    }

    private func createDecksJSON(deckId: Int64, deckName: String) -> String {
        let now = Int64(Date().timeIntervalSince1970)
        return """
        {"1":{"id":1,"name":"Default","mod":\(now),"usn":-1,"lrnToday":[0,0],"revToday":[0,0],"newToday":[0,0],"timeToday":[0,0],"collapsed":false,"browserCollapsed":false,"desc":"","dyn":0,"conf":1,"extendNew":0,"extendRev":0},"\(deckId)":{"id":\(deckId),"name":"\(escapeJSON(deckName))","mod":\(now),"usn":-1,"lrnToday":[0,0],"revToday":[0,0],"newToday":[0,0],"timeToday":[0,0],"collapsed":false,"browserCollapsed":false,"desc":"","dyn":0,"conf":1,"extendNew":0,"extendRev":0}}
        """
    }

    private func createDconfJSON() -> String {
        return """
        {"1":{"id":1,"name":"Default","mod":0,"usn":0,"maxTaken":60,"autoplay":true,"timer":0,"replayq":true,"new":{"bury":false,"delays":[1,10],"initialFactor":2500,"ints":[1,4,0],"order":1,"perDay":20},"rev":{"bury":false,"ease4":1.3,"ivlFct":1,"maxIvl":36500,"perDay":200,"hardFactor":1.2},"lapse":{"delays":[10],"leechAction":1,"leechFails":8,"minInt":1,"mult":0},"dyn":false}}
        """
    }

    private func escapeJSON(_ string: String) -> String {
        return string
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "\n", with: "\\n")
            .replacingOccurrences(of: "\r", with: "\\r")
            .replacingOccurrences(of: "\t", with: "\\t")
    }
}
