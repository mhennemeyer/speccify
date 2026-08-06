import Foundation

/// Access to the app's iCloud ubiquity container.
///
/// The resolver is injected so the whole storage layer is testable without an
/// entitlement, an account or a network: production uses
/// `FileManager.url(forUbiquityContainerIdentifier:)`, tests hand in a temp
/// directory.
///
/// Two rules encoded here:
///
/// * Resolution must not happen on the main thread — Apple: "Always call the
///   URLForUbiquityContainerIdentifier: method from a background thread […]
///   does not always return immediately." Call `warmUp()` once, off-main, and
///   read the cached value afterwards.
/// * `nil` means document storage is unavailable (signed out, iCloud Drive
///   off, capability never granted). That is a state, not an error.
public actor ICloudContainer {
    public static let containerID = "iCloud.com.example.myapp"

    private let resolveURL: @Sendable () -> URL?
    private var cached: URL??          // .none = not resolved yet

    public init(resolveURL: @escaping @Sendable () -> URL? = {
        FileManager.default.url(forUbiquityContainerIdentifier: ICloudContainer.containerID)
    }) {
        self.resolveURL = resolveURL
    }

    /// Resolves once and caches. Safe to call repeatedly; call it at launch
    /// from a detached task, never from a SwiftUI body or a @MainActor init.
    @discardableResult
    public func warmUp() -> URL? {
        if let cached { return cached }
        let url = resolveURL()
        cached = url
        return url
    }

    public var isAvailable: Bool { warmUp() != nil }

    /// `<container>/Documents` — only what lives under here is visible to the
    /// user in iCloud Drive. Files in the container root sync but stay hidden.
    public func documentsURL() -> URL? {
        warmUp()?.appendingPathComponent("Documents", isDirectory: true)
    }

    public func projectURL(id: String) -> URL? {
        documentsURL()?
            .appendingPathComponent("projects", isDirectory: true)
            .appendingPathComponent(id, isDirectory: true)
    }

    /// Idempotent; throws when there is no container.
    @discardableResult
    public func ensureProjectURL(id: String) throws -> URL {
        guard let url = projectURL(id: id) else {
            throw CocoaError(.ubiquitousFileUnavailable)
        }
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }
}
