import Foundation

/// A trial period you own, because Apple only offers free trials for
/// subscriptions.
///
/// The interesting part is not the arithmetic — it is the high-water mark.
/// `start + 7 days < now` is defeated by setting the clock back, so the highest
/// time ever seen is carried along and used as the lower bound. Setting the
/// clock *forward* only shortens the trial, which is the harmless direction.
///
/// Deliberately free of StoreKit so the edge cases are testable without a
/// store environment.
struct TrialState: Equatable, Codable {
    static let duration: TimeInterval = 7 * 24 * 60 * 60

    var start: Date
    /// Highest system time ever observed. Never decreases.
    var highWaterMark: Date

    init(start: Date, highWaterMark: Date? = nil) {
        self.start = start
        self.highWaterMark = max(highWaterMark ?? start, start)
    }

    /// The time used for the calculation — never earlier than what we saw.
    func effectiveDate(_ now: Date) -> Date { max(now, highWaterMark) }

    var end: Date { start.addingTimeInterval(Self.duration) }

    func remaining(at now: Date) -> TimeInterval {
        max(0, end.timeIntervalSince(effectiveDate(now)))
    }

    func isActive(at now: Date) -> Bool { remaining(at: now) > 0 }

    /// Round up, so the final day reads "1 day left" rather than "0 days left".
    func daysRemaining(at now: Date) -> Int {
        let seconds = remaining(at: now)
        return seconds <= 0 ? 0 : max(1, Int(ceil(seconds / 86_400)))
    }

    mutating func observe(_ now: Date) {
        highWaterMark = max(highWaterMark, now)
    }

    /// Merge two stores: the earlier start and the higher mark win.
    ///
    /// This is what makes a reinstall or a second device continue the trial
    /// instead of restarting it.
    static func merge(_ a: TrialState?, _ b: TrialState?) -> TrialState? {
        switch (a, b) {
        case (nil, nil): return nil
        case let (value?, nil): return value
        case let (nil, value?): return value
        case let (x?, y?):
            return TrialState(
                start: min(x.start, y.start),
                highWaterMark: max(x.highWaterMark, y.highWaterMark)
            )
        }
    }
}

/// Where the start date lives. No single store has every property you need:
///
/// - `UserDefaults` travels in backups → survives a new device, dies on delete.
/// - Keychain survives app deletion on the same device, but not a new device.
/// - `NSUbiquitousKeyValueStore` spans devices on one Apple ID, but needs iCloud.
///
/// Write to all of them, read the union. Behind a protocol, because
/// `NSUbiquitousKeyValueStore` cannot be faked in tests — and this is exactly
/// the code that decides between "seven days total" and "seven days per device".
protocol TrialStore {
    func read() -> TrialState?
    func write(_ state: TrialState)
}

extension Array where Element == TrialStore {
    /// Load the union and backfill every store that is behind.
    func loadOrStart(now: Date = Date()) -> TrialState {
        var merged = reduce(TrialState?.none) { TrialState.merge($0, $1.read()) }
            ?? TrialState(start: now)
        merged.observe(now)
        forEach { $0.write(merged) }
        return merged
    }
}
