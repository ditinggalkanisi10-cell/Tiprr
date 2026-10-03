# TIPRR: devnet foundation

## Current scope

This is the first, **devnet-only integration-ready build** approved by the user. It is not a launched production tipping service. The application never fabricates X accounts, payments, balances, blockchain receipts, or UsePaid eligibility. The home-page conversation is an explicitly labeled illustrative animation, not bot activity.

Implemented: real public devnet JSON-RPC, a server-only isolated devnet signer, Phantom/Solflare ownership verification, secure sessions, generic SOL/SPL deposit construction and on-chain receipt verification, immutable account journal and atomic reservations, durable withdrawal state machine, history, protected administration, scheduled reconciliation, and honest integration status.

Deferred by user: official X OAuth/API activation and bot ingestion, X identity linking, live X replies, claims, UsePaid. X API adapter building blocks and a strict command parser exist but are not a running bot. Configuring environment variables alone does NOT activate the unfinished identity/tipping phase.

## Configuration

Existing `backend/.env` and `frontend/.env` are not to be committed. Keep `MONGO_URL`, `DB_NAME` and `REACT_APP_BACKEND_URL` as provided. See `backend/.env.example` for required names, never values.

`python backend/bootstrap_devnet.py` generates missing local development settings without printing the signer. It never overwrites existing values. The operational key is an isolated devnet key in the server environment, not in the database or browser. Replace local environment custody with a professional secret manager/signing provider before any mainnet build. The backend rejects money movement unless BOT_MODE=development, SOLANA_NETWORK=devnet, and the RPC's genesis hash matches the configured devnet genesis hash.

Public RPC is supplied by the Solana Foundation, not a self-operated validator. It has rate limits and no SLA. `SOLANA_RPC_URL` can point to a private devnet provider without frontend changes. Do not point the current build at mainnet.

The treasury needs enough **devnet** SOL for payout fees and token-account rent. Its public address, never its secret, is shown on System Status. Test SOL is available from the official Solana faucet linked there. Mainnet BONK/USDC/WIF mints do not exist on devnet; add a supported devnet mint instead. Brand token examples on the landing page are illustrative of the planned mainnet product, not preloaded test assets.

## Real wallet and deposit flow

1. Connect Phantom or Solflare (desktop extension or mobile wallet browser).
2. Sign a unique, expiring, origin- and devnet-bound ownership challenge.
3. Server verifies Ed25519 ownership and issues a Secure HttpOnly session cookie. CSRF uses a session-bound header token plus Origin validation; it does NOT rely on SameSite because embedded preview proxies may rewrite that attribute. The CSRF token stays in app memory; it is not a wallet/private key.
4. Select SOL or resolve a custom devnet token mint. The server reads decimals/program directly from Solana. Unknown display metadata uses an abbreviated mint, never guessed symbols.
5. Backend builds a deposit with exact source, destination, asset, amount and unique memo. Wallet signs this exact message.
6. Backend compares and verifies the signed message, persists signature/bytes BEFORE submission, then checks finalized transaction receipt, instructions and exact net received balance. Only then is the account credited.

**Do not directly transfer to the displayed treasury address.** Shared-treasury attribution requires the prepared deposit reference and verified source wallet. Unreferenced direct transfers are not automatically credited. This intentional first-build architecture should be replaced/extended by per-user monitored deposit destinations if address-only deposits are needed.

SPL transfers use TransferChecked and derive/create idempotent ATAs using the actual token program. The conservative first-build policy rejects mints with freeze authority, all Token-2022 extensions, unsupported decimals and non-mints. Extension-free compatible Token-2022 mints use the same generic adapter. No claims are made about supporting every Token-2022 mint.

## Ledger and payments

All internal financial amounts use integer base units, bounded to signed int64. API amounts/base-unit values are strings so JavaScript does not lose precision. Available/reserved balances are projections, atomically changed in the SAME MongoDB update as append-only journal entries. No read-modify-write balance race. Duplicate references cannot apply the same operation twice; settle/release are mutually exclusive.

The provided database is standalone MongoDB and cannot provide multi-document transactions. The initial design therefore deliberately uses one aggregate per account, not fake multi-document transaction semantics. Incoming account journals are capped at 10,000 events, with finalization allowed beyond that cap. This is an explicit development scalability limitation, not the requested final PostgreSQL accounting system.

Withdrawals are persisted with per-user idempotency keys. Their reservation is atomic. Competing workers may build a transaction, but only the compare-and-set winner's persisted signed bytes are submitted. Confirmation retries and submission retries never re-sign an existing operation. Confirmed failures release balances. An expired/unresolved signature remains reserved and requires manual reconciliation—there is no unsafe automatic resend/release. No admin force-complete or fund-changing endpoint exists in this build.

The operational devnet wallet pays payout fees and ATA rent; production fee policy and treasury liquidity monitoring are follow-up requirements.

## Background work

`.emergent/crons.yml` requests devnet reconciliation every 15 minutes. `/api/cron/reconcile` requires WEBHOOK_CRON_SECRET, validates the envelope, records a unique run ID, acknowledges immediately, and processes pending records asynchronously. Records remain durable if execution is interrupted and are picked up by a later reconciliation. Closing the browser does not prevent scheduled reconciliation.

This is **not a continuously running X bot**. The real X listener/queue/reply worker is a future integration phase. It must use official X APIs with correct entitlements and separate payment/reply retries.

## Administration

ADMIN_WALLETS is intentionally empty initially. Add the public address of an operator, reconnect/verify that wallet, and use `/admin`. Verification does not confer admin privileges unless the server allowlist matches. Administrators can inspect aggregate statistics and recent payments, never signer secrets.

## Production blockers / next phase

- Managed PostgreSQL schema and migration with immutable ledger tables and serializable/row-locked reservations.
- Official X OAuth 2.0 PKCE, encrypted token storage, stable-X-ID identity linking and safe account linking (wallet-only development accounts must not be confused with X identities).
- Durable X listener, ingestion queue, globally unique x_post_id processing, recipient resolution, per-asset tip/daily limits and reply-only retries.
- X-authenticated multi-asset pending claims and payout authorization. Current claim endpoints reject unverified X identities and are explicitly not active.
- UsePaid official API documentation and credentials; real provider eligibility, not country guesses.
- Professional custody/signing and secret management, dedicated RPC, operational monitoring, reconciliation tooling, funded fee reserve and independent security assessment.
- Real end-to-end SOL/SPL/custom-token/claims testing with configured X and funding, before any production-readiness claim.

## Verification

`cd backend && pytest tests -q` exercises the devnet foundation. Browser tests and reports are under `test_reports`. Backend tests use disposable signed wallets; no frontend fake-wallet path exists. A passing devnet unit suite is not evidence that the deferred production bot acceptance tests pass.