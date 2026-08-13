import Foundation

/// File I/O through `NSFileCoordinator`, with explicit conflict resolution.
///
/// Every read and write of container files goes through here — including for
/// projects that are *not* in iCloud. Coordination is harmless for local
/// files, and one code path removes the entire "works locally, corrupts in
/// iCloud" class of bug.
public enum CoordinatedFile {

    /// Coordinated read. Resolves outstanding conflicts first, so callers
    /// never observe a file that still has unresolved versions attached.
    public static func read(_ url: URL) throws -> Data {
        resolveConflicts(at: url)
        var coordError: NSError?
        var result: Result<Data, Error>?
        NSFileCoordinator().coordinate(readingItemAt: url, options: [], error: &coordError) { actual in
            // `actual`, not `url`: the coordinator may substitute a URL.
            result = Result { try Data(contentsOf: actual) }
        }
        if let coordError { throw coordError }
        return try result!.get()
    }

    /// Coordinated, atomic write.
    public static func write(_ data: Data, to url: URL) throws {
        var coordError: NSError?
        var ioError: Error?
        NSFileCoordinator().coordinate(writingItemAt: url, options: [.forReplacing], error: &coordError) { actual in
            do {
                try FileManager.default.createDirectory(
                    at: actual.deletingLastPathComponent(), withIntermediateDirectories: true)
                try data.write(to: actual, options: .atomic)
            } catch { ioError = error }
        }
        if let coordError { throw coordError }
        if let ioError { throw ioError }
    }

    /// Coordinated delete; no-op when the file is already gone.
    public static func delete(_ url: URL) throws {
        guard FileManager.default.fileExists(atPath: url.path) else { return }
        var coordError: NSError?
        var ioError: Error?
        NSFileCoordinator().coordinate(writingItemAt: url, options: [.forDeleting], error: &coordError) { actual in
            do { try FileManager.default.removeItem(at: actual) } catch { ioError = error }
        }
        if let coordError { throw coordError }
        if let ioError { throw ioError }
    }

    /// Last-writer-wins conflict resolution.
    ///
    /// Plain files (unlike NSDocument) keep unresolved conflict versions until
    /// something resolves them, and the symptoms of ignoring that look like
    /// random data loss. Best-effort and a no-op for local files.
    ///
    /// Be aware of the cost: the loser's edit is discarded. If your data
    /// cannot tolerate that, you need per-field merging — or an append-only
    /// structure, which has no conflicts to resolve in the first place.
    public static func resolveConflicts(at url: URL) {
        guard let conflicts = NSFileVersion.unresolvedConflictVersionsOfItem(at: url),
              !conflicts.isEmpty else { return }

        var versions: [NSFileVersion] = []
        if let current = NSFileVersion.currentVersionOfItem(at: url) { versions.append(current) }
        versions.append(contentsOf: conflicts)

        let newest = versions.enumerated().max { lhs, rhs in
            (lhs.element.modificationDate ?? .distantPast) < (rhs.element.modificationDate ?? .distantPast)
        }
        if let newest, newest.element != NSFileVersion.currentVersionOfItem(at: url) {
            try? newest.element.replaceItem(at: url)
        }
        for conflict in conflicts { conflict.isResolved = true }
        try? NSFileVersion.removeOtherVersionsOfItem(at: url)
    }
}
