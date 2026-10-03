# TIPRR Product Requirements and Build Record

## Original problem statement

> Build a full-stack production-ready application called TIPRR. TIPRR is an X tipping bot for Solana. Login with X → connect/deposit a Solana wallet → deposit any supported Solana asset → tweet `/tiprr 0.1 SOL @username` or `/tiprr 10 BONK @username`. TIPRR detects the official X post, identifies the sender by permanent X user ID, checks the exact asset balance, resolves the recipient and payment route, sends the asset and replies directly to the tweet. The website is the account, balance, deposit, withdrawal and claim interface; X is the primary tipping interface. Keep the product simple and focused, not a DEX, launchpad, trading platform, social network or AI agent.

Original requirements cover official X OAuth 2.0, an independent real X bot, Solana native/SPL/custom/compatible Token-2022 support, authoritative mint identity and on-chain decimals, integer accounting, confirmed deposits, immutable ledger, atomic balance reservations, UsePaid eligibility or X-ID-secured claims, backend custody/signing, generic payment adapters, PENDING/PROCESSING/COMPLETED/FAILED/CANCELLED states, unique x_post_id, independent payment/reply retries, dashboard/deposit/withdraw/history/profile/admin, limits, audit/security, PostgreSQL, persistent independent workers, secure environment configuration, and real end-to-end SOL/SPL/custom/claim/concurrency/replay acceptance tests. The requested brand is minimal, playful, clean, dark black/white with a pixel-art robot and the tagline “Tip anyone on X.”

## User-approved first-phase changes (2026-10-03)

- “Build solana rpc enpoint and secure confuguration first, other else later just build intergretatoj ready fisrt without real x outh and api bot acces.” First phase is integration-ready, NOT a live production X bot.
- Solana devnet with an isolated development signer; no real funds.
- Use the provided MongoDB for this first build; document PostgreSQL as a later requirement.
- UsePaid explicitly unconfigured; claim route is planned where appropriate but cannot activate without verified X identity.
- “Untuk di web buatkan contoh animasi botnya berjalan seperti ketik /tippr 0.02 @tiprrx gitu terus ada balesannya tampilan x gitu animasinya…” Implemented an explicitly illustrative animated X-like thread with the canonical syntax `/tiprr 0.02 SOL @tiprrx`.
- No X/UsePaid credentials supplied. Do not create fake logins, bots, balances, receipts or production integrations.

## Personas

1. Sender: funds a TIPRR account once, tips through X without signing each tip.
2. Recipient: authenticates the correct X identity and proves wallet ownership to claim assets.
3. Operator: monitors RPC/bot/integrations, funding, reconciliation, failed payments and audited ledger state.
4. First-phase devnet tester: proves real wallet ownership and exercises development deposit/withdraw flows without an X account or real money.

## Architecture decisions

- React 19/React Router, shadcn Dialog/Button/Input, custom responsive dark visual system, generated bitmap pixel mascot, animated illustrative thread. Landing page is required by the original specification; complete workspace routes are also implemented.
- FastAPI backend on existing port8001. React accesses only REACT_APP_BACKEND_URL. Existing MONGO_URL remains unchanged.
- Standalone MongoDB: per-user atomic aggregate with balances + append-only journal in the same atomic write. Available/reserved are projections; immutable journal entries are the financial event record. No false multi-document transaction guarantees. 10,000 incoming journal-entry cap; settlement/releases remain permitted. PostgreSQL migration remains P0 before production.
- Real official public devnet JSON-RPC, checked by full genesis hash. Not a self-operated validator. Server-only generated isolated signer, devnet-only guard, restrictive environment file permissions; no key material in UI/database/logs/API responses. Production custody is explicitly deferred.
- Real Phantom/Solflare injected wallet connect + domain/network/nonce/expiry-bound Ed25519 signature verification. This is a development wallet identity, not fabricated X auth. X-linked accounts cannot be assumed from a wallet or handle.
- Secure HttpOnly cookie, session-bound in-memory CSRF header token, exact Origin/CORS checks. Public embedding proxy rewrites SameSite to None/Partitioned; security must not rely on the external cookie's SameSite value.
- Server-created shared treasury deposit with exact prepared message and unique memo; source wallet signature, asset/program, destination, instruction amount and finalized net receipt all verified. Arbitrary direct transfers are not auto-credited.
- Generic native/SPL transfer builders, TransferChecked + actual-program ATA derivation. Conservative rejection of freeze-authority mints and Token-2022 extensions. Unknown metadata displays shortened authoritative mint rather than a guessed symbol.
- Persistent payout state machine with atomic reservation and CAS persistence of signed bytes BEFORE broadcast; only identical bytes retried. Unresolved expired signatures stay reserved for manual reconciliation, never blindly re-signed.
- Authenticated scheduled reconciliation every15min in .emergent/crons.yml. Durable payment/deposit records survive browser closure and interrupted processing. This is not an enabled continuous X listener.
- X official API building blocks + parser/asset resolver exist; actual OAuth linking, ingestion/processing/reply workflows and claims are deliberately blocked. UsePaid shows exact missing setup, never eligibility by country.

## Static core requirements

- Permanent X ID; canonical token mint; exact integer financial amounts.
- No frontend-asserted credit, no negative balance, no double-spend, no duplicate post/payment execution.
- Real chain finality before completion. Independent reply retries must never re-send a payment.
- Claims require verified X ID + wallet ownership; no username-only claims.
- No private key or OAuth credential leakage; authenticated internals/admin; auditable append-only accounting.
- Devnet/no-real-funds warning; explicitly unconfigured integrations must not pretend to work.
- Simple user experience, responsive pages, useful empty/loading/error states and inspectable transactions.

## Implemented — 2026-10-03

- Dark monochrome TIPRR website, pixel robot, actual animated example command/reply with play/pause/replay and SOL/BONK/USDC examples clearly labeled illustrative, no funds moved.
- Dashboard, deposit, withdraw, activity/filter/search, claims gate, connections/profile, integration status, protected administrator page; mobile layouts and navigation.
- Live devnet RPC status/genesis verification; secure server-side development signing configuration; honest X/UsePaid configuration states.
- Real wallet challenges, signature verification, one-use nonce/expiry, cookie sessions, CSRF/Origin protection, logout and server authorization; wallet allowlist admin.
- Persistent tokens, accounts, balances/journal, deposits, payment records, jobs, audit entries and unique constraints; precision-safe amount parser; strict /tiprr parser and mint-first/ambiguity-safe resolver.
- On-chain custom mint validation and generic SOL/SPL deposit construction, exact-message verification, finalized receipt checks and idempotent ledger credit.
- Withdrawal validation, idempotency conflict checking, atomic available/reserved journal, persisted signed transactions, broadcast/reconciliation and safe unresolved-payment handling.
- Transaction history with detail dialog including mint, integer base units, source/destination, timestamp/status and explorer signature.
- Authenticated scheduled reconciliation with run-ID deduplication, auth-before-body validation and immediate response.
- Setup/limitations guide at /app/TIPRR_SETUP.md and backend/.env.example. No production-readiness claim.

## Verification — 2026-10-03

- Frontend production compilation succeeds. Non-blocking SDK sourcemap warnings from upstream packages remain.
- Desktop screenshots verified home, X config dialog, dashboard, deposit and status; testing agent checked desktop/mobile routes and no horizontal overflow.
- First test iteration found proxy cookie rewriting and close-dialog/navigation race. Fixed with session-bound CSRF protection and immediate closed-dialog unmount, respectively.
- Second regression: **25 passed, 1 skipped**. Validated real signed wallet auth, precision rules, authorization/CSRF/Origin checks, malformed transactions, atomic reservation race, idempotency and cron authentication/replay. See test_reports/iteration_2.json.
- **LIVE DEVNET DEPOSIT/WITHDRAW SETTLEMENT NOT VERIFIED:** the public devnet faucet was unavailable/rate-limited. No balances or confirmations were fabricated. Full real SOL/SPL/custom-token settlement still requires funding and verification; passing foundational tests is not full production acceptance.
- X OAuth, live X detection/replies, live claims and UsePaid are intentionally not active per the revised phase scope.

## Prioritized backlog / next tasks

### P0 — required before live tipping or production
1. Fund disposable development wallets and treasury fee reserve with devnet SOL; complete actual SOL/SPL/custom/Token-2022 finalized deposit/payout tests, including failure, expiration, receipt mismatches and restart recovery.
2. Official X OAuth2 PKCE + encrypted token persistence/refresh + stable-ID linking with secure development-wallet account migration/linking.
3. Official X listener, durable ingestion/processing/reply queues, global x_post_id idempotency, sender validation, recipient resolution, per-asset per-tip/daily/rate limits; independently retry X replies.
4. Multi-asset pending claims keyed by verified X ID; claim-all with per-asset settlement and replay/concurrency protection. Current buttons/endpoints are gated, not a working claim engine.
5. PostgreSQL migration/schema/immutable ledger and real database transactions; stronger operational custody/signing provider and managed secrets.
6. Production-grade private RPC, provider monitoring, fee/rent reserve policy, reconciliation/manual-review tooling and independent security assessment.
7. Correct X-authorized routing/payment acceptance tests and real world operational monitoring before any mainnet rollout.

### P1
- Obtain official UsePaid documentation/access and implement actual eligibility/payment states/webhook verification; retain secure claims fallback.
- Per-user monitored deposit destinations and recovery path for unreferenced transfers, replacing/augmenting current required signed-reference flow.
- Broader audited Token-2022 extension compatibility, trusted on-chain metadata resolution and verified token mappings.
- Admin filtering, per-asset volumes, audit exploration and operational alerts; cursor-paginated history beyond latest100 rows.
- SOL fee/rent estimation and treasury liquidity visibility in the user/operator experience.

### P2
- Shareable verified tip receipts and one-click claim links in real X replies.
- More animation scenarios, localization and accessibility polish; larger-wallet/provider compatibility.

## Next session handoff

Read TIPRR_SETUP.md, this PRD and test_reports/iteration_2.json first. Do not call the app a production-ready bot. Do not enable X from env values alone: identity + worker phase remains unimplemented. Do not accept arbitrary manual treasury deposits as credited. Keep the provided environment URLs and Mongo URI intact. Test accounts use ephemeral generated keys; there is intentionally no shared wallet private key in test_credentials.md.