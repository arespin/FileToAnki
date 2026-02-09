import SwiftUI

struct CardPreviewView: View {
    @ObservedObject var viewModel: DeckViewModel
    @State private var editingCard: Flashcard?
    @State private var editFront: String = ""
    @State private var editBack: String = ""

    var body: some View {
        VStack(spacing: 0) {
            // Header with deck name and card count
            VStack(spacing: 8) {
                TextField("Deck Name", text: $viewModel.deckName)
                    .font(.headline)
                    .textFieldStyle(.roundedBorder)
                    .padding(.horizontal)

                HStack {
                    Text("\(viewModel.flashcards.count) cards")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    Spacer()

                    Button(action: viewModel.addCard) {
                        Label("Add Card", systemImage: "plus")
                            .font(.subheadline)
                    }
                }
                .padding(.horizontal)
            }
            .padding(.vertical, 12)
            .background(Color(UIColor.systemGroupedBackground))

            // Card list
            List {
                ForEach(viewModel.flashcards) { card in
                    CardRow(card: card, onEdit: {
                        editingCard = card
                        editFront = card.front
                        editBack = card.back
                    })
                }
                .onDelete(perform: viewModel.deleteCard)
            }
            .listStyle(.plain)

            // Export button
            VStack {
                Button(action: viewModel.exportDeck) {
                    HStack {
                        if viewModel.state == .exporting {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Image(systemName: "square.and.arrow.up")
                        }
                        Text(viewModel.state == .exported ? "Export Again" : "Export to Anki")
                    }
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(viewModel.flashcards.isEmpty ? Color.gray : Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                }
                .disabled(viewModel.flashcards.isEmpty || viewModel.state == .exporting)
                .padding()
            }
            .background(Color(UIColor.systemBackground))
        }
        .sheet(item: $editingCard) { card in
            CardEditSheet(
                front: $editFront,
                back: $editBack,
                onSave: {
                    viewModel.updateCard(card, front: editFront, back: editBack)
                    editingCard = nil
                },
                onCancel: {
                    editingCard = nil
                }
            )
        }
    }
}

struct CardRow: View {
    let card: Flashcard
    let onEdit: () -> Void

    @State private var isFlipped = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(isFlipped ? "Back" : "Front")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .textCase(.uppercase)

                Spacer()

                Button(action: onEdit) {
                    Image(systemName: "pencil")
                        .foregroundColor(.blue)
                }
                .buttonStyle(.plain)
            }

            Text(isFlipped ? card.back : card.front)
                .font(.body)
                .lineLimit(3)

            Button(action: { isFlipped.toggle() }) {
                HStack {
                    Image(systemName: "arrow.triangle.2.circlepath")
                    Text("Flip")
                }
                .font(.caption)
                .foregroundColor(.blue)
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 8)
        .contentShape(Rectangle())
        .onTapGesture {
            isFlipped.toggle()
        }
    }
}

struct CardEditSheet: View {
    @Binding var front: String
    @Binding var back: String
    let onSave: () -> Void
    let onCancel: () -> Void

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Question (Front)")) {
                    TextEditor(text: $front)
                        .frame(minHeight: 100)
                }

                Section(header: Text("Answer (Back)")) {
                    TextEditor(text: $back)
                        .frame(minHeight: 100)
                }
            }
            .navigationTitle("Edit Card")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save", action: onSave)
                        .disabled(front.isEmpty || back.isEmpty)
                }
            }
        }
    }
}

#Preview {
    let viewModel = DeckViewModel()
    return CardPreviewView(viewModel: viewModel)
}
