import Foundation
import StoreKit

/// Purchase and entitlement handling for a single non-consumable unlock.
///
/// Three of the four rules here are ordering problems, and all four are the
/// kind you only notice in production:
///
/// 1. Subscribe to `Transaction.updates` *before* checking entitlements —
///    otherwise a transaction arriving during startup is lost.
/// 2. Read `currentEntitlements` on every launch; the purchase may have
///    happened on another device.
/// 3. Ignore `.unverified` results — that check is the whole point of the
///    signature.
/// 4. `.pending` is not a failure: under Ask to Buy the purchase completes
///    later through `Transaction.updates`.
@MainActor
final class StoreService: ObservableObject {
    static let productID = "com.example.app.pro"

    @Published private(set) var product: Product?
    @Published private(set) var isPurchased = false
    @Published private(set) var isWorking = false
    /// Set for real problems only — never for `.pending`.
    @Published private(set) var errorMessage: String?
    /// Set when a purchase is waiting for approval.
    @Published private(set) var pendingNotice: String?

    private var updates: Task<Void, Never>?

    func start() {
        guard updates == nil else { return }
        // Listen first, then check: see rule 1.
        updates = Task { [weak self] in
            for await update in Transaction.updates {
                await self?.handle(update)
            }
        }
        Task { await refreshEntitlements() }
        Task { await loadProduct() }
    }

    func stop() {
        updates?.cancel()
        updates = nil
    }

    func loadProduct() async {
        do {
            product = try await Product.products(for: [Self.productID]).first
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refreshEntitlements() async {
        for await entitlement in Transaction.currentEntitlements {
            guard case .verified(let transaction) = entitlement else { continue }
            if transaction.productID == Self.productID, transaction.revocationDate == nil {
                isPurchased = true
                return
            }
        }
        isPurchased = false
    }

    func purchase() async {
        guard let product else {
            errorMessage = "The product is unavailable right now."
            return
        }
        isWorking = true
        errorMessage = nil
        pendingNotice = nil
        defer { isWorking = false }
        do {
            switch try await product.purchase() {
            case .success(let verification):
                await handle(verification)
            case .userCancelled:
                break
            case .pending:
                pendingNotice = "This purchase is waiting for approval."
            @unknown default:
                break
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// App Review requires this for non-consumables.
    func restore() async {
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        do {
            try await AppStore.sync()
            await refreshEntitlements()
            if !isPurchased {
                errorMessage = "No purchase was found for this Apple account."
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func handle(_ result: VerificationResult<Transaction>) async {
        guard case .verified(let transaction) = result else { return }
        if transaction.productID == Self.productID, transaction.revocationDate == nil {
            isPurchased = true
        }
        await transaction.finish()
    }

    deinit { updates?.cancel() }
}
