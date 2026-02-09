import SwiftUI

struct FilePickerView: View {
    @Binding var showingFilePicker: Bool

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            // Icon
            ZStack {
                Circle()
                    .fill(Color.blue.opacity(0.1))
                    .frame(width: 120, height: 120)

                Image(systemName: "doc.badge.plus")
                    .font(.system(size: 50))
                    .foregroundColor(.blue)
            }

            // Title and description
            VStack(spacing: 12) {
                Text("Upload a File")
                    .font(.title)
                    .bold()

                Text("Select a document to extract key facts and create Anki flashcards")
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }

            // Upload button
            Button(action: {
                showingFilePicker = true
            }) {
                HStack {
                    Image(systemName: "plus.circle.fill")
                    Text("Choose File")
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .padding(.horizontal, 32)

            // Supported formats
            VStack(spacing: 8) {
                Text("Supported formats")
                    .font(.caption)
                    .foregroundColor(.secondary)

                HStack(spacing: 12) {
                    FormatBadge(text: "PDF")
                    FormatBadge(text: "TXT")
                    FormatBadge(text: "DOCX")
                    FormatBadge(text: "Images")
                }
            }

            Spacer()
        }
        .padding()
    }
}

struct FormatBadge: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption)
            .fontWeight(.medium)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(Color.gray.opacity(0.15))
            .cornerRadius(6)
    }
}

#Preview {
    FilePickerView(showingFilePicker: .constant(false))
}
