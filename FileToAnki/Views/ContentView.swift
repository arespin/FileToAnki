import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = DeckViewModel()
    @State private var showingFilePicker = false

    var body: some View {
        NavigationView {
            Group {
                switch viewModel.state {
                case .idle:
                    FilePickerView(showingFilePicker: $showingFilePicker)

                case .parsing, .extracting:
                    ProcessingView(message: viewModel.progressMessage)

                case .reviewing, .exporting, .exported:
                    CardPreviewView(viewModel: viewModel)

                case .error:
                    ErrorView(
                        message: viewModel.errorMessage ?? "An error occurred",
                        onRetry: { viewModel.reset() }
                    )
                }
            }
            .navigationTitle("FileToAnki")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    if viewModel.state == .reviewing || viewModel.state == .exported {
                        Button("New") {
                            viewModel.reset()
                        }
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    NavigationLink(destination: SettingsView()) {
                        Image(systemName: "gear")
                    }
                }
            }
        }
        .sheet(isPresented: $showingFilePicker) {
            DocumentPicker { url in
                Task {
                    await viewModel.processFile(url: url)
                }
            }
        }
        .sheet(isPresented: $viewModel.showingExportSheet) {
            if let url = viewModel.exportedFileURL {
                ActivityView(activityItems: [url])
            }
        }
    }
}

struct ErrorView: View {
    let message: String
    let onRetry: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 50))
                .foregroundColor(.orange)

            Text("Something went wrong")
                .font(.headline)

            Text(message)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Button("Try Again") {
                onRetry()
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }
}

struct SettingsView: View {
    @AppStorage("claudeAPIKey") private var apiKey: String = ""
    @State private var editingKey: String = ""
    @State private var isEditing = false

    var body: some View {
        Form {
            Section(header: Text("API Configuration")) {
                if isEditing {
                    SecureField("API Key", text: $editingKey)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)

                    HStack {
                        Button("Cancel") {
                            editingKey = ""
                            isEditing = false
                        }

                        Spacer()

                        Button("Save") {
                            apiKey = editingKey
                            editingKey = ""
                            isEditing = false
                        }
                        .disabled(editingKey.isEmpty)
                    }
                } else {
                    HStack {
                        Text("Claude API Key")
                        Spacer()
                        if apiKey.isEmpty {
                            Text("Not set")
                                .foregroundColor(.secondary)
                        } else {
                            Text("••••••••" + apiKey.suffix(4))
                                .foregroundColor(.secondary)
                        }
                    }

                    Button("Change API Key") {
                        isEditing = true
                    }
                }
            }

            Section(header: Text("About")) {
                HStack {
                    Text("Version")
                    Spacer()
                    Text("1.0.0")
                        .foregroundColor(.secondary)
                }

                Link("Get API Key from Anthropic",
                     destination: URL(string: "https://console.anthropic.com/")!)
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    ContentView()
}
