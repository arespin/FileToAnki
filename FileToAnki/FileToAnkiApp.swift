import SwiftUI

@main
struct FileToAnkiApp: App {
    @AppStorage("claudeAPIKey") private var apiKey: String = ""

    var body: some Scene {
        WindowGroup {
            if apiKey.isEmpty {
                APIKeySetupView()
            } else {
                ContentView()
            }
        }
    }
}

struct APIKeySetupView: View {
    @AppStorage("claudeAPIKey") private var apiKey: String = ""
    @State private var inputKey: String = ""

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 60))
                    .foregroundColor(.blue)

                Text("FileToAnki")
                    .font(.largeTitle)
                    .bold()

                Text("Enter your Claude API key to get started")
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)

                VStack(alignment: .leading, spacing: 8) {
                    Text("API Key")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    SecureField("sk-ant-...", text: $inputKey)
                        .textFieldStyle(.roundedBorder)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                }
                .padding(.horizontal)

                Button(action: {
                    apiKey = inputKey
                }) {
                    Text("Continue")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(inputKey.isEmpty ? Color.gray : Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
                .disabled(inputKey.isEmpty)
                .padding(.horizontal)

                Link("Get an API key from Anthropic",
                     destination: URL(string: "https://console.anthropic.com/")!)
                    .font(.caption)
            }
            .padding()
            .navigationBarHidden(true)
        }
    }
}
