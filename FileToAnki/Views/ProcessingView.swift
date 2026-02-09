import SwiftUI

struct ProcessingView: View {
    let message: String

    @State private var rotation: Double = 0

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            // Animated icon
            ZStack {
                Circle()
                    .stroke(Color.blue.opacity(0.2), lineWidth: 4)
                    .frame(width: 80, height: 80)

                Circle()
                    .trim(from: 0, to: 0.3)
                    .stroke(Color.blue, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                    .frame(width: 80, height: 80)
                    .rotationEffect(.degrees(rotation))
                    .onAppear {
                        withAnimation(.linear(duration: 1).repeatForever(autoreverses: false)) {
                            rotation = 360
                        }
                    }

                Image(systemName: "brain.head.profile")
                    .font(.system(size: 30))
                    .foregroundColor(.blue)
            }

            VStack(spacing: 12) {
                Text("Processing")
                    .font(.title2)
                    .bold()

                Text(message)
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }

            Spacer()

            Text("This may take a moment...")
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.bottom, 32)
        }
        .padding()
    }
}

#Preview {
    ProcessingView(message: "Extracting key facts with AI...")
}
