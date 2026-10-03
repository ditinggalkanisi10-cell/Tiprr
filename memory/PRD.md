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

## Mascot update — 2026-10-03 (superseded by wordmark below)

- User supplied a pixel robot reference and requested a cleaner redraw preserving its recognizable art: “Dominan hitam, outline dan mata putih, background transparan” and “Edit karakternya draw ulamg biar lebih oke”.
- Generated a reference-based redraw retaining the oversized stepped head, antenna, square eyes and compact body. Prepared true transparent, pure black/white PNG assets (no green background or baked transparency pattern).
- Shared Bot component now uses `/tiprr-mascot-v2.png` throughout header, hero, illustrative bot replies, dashboard/claims/activity empty states and footer. Favicon updated to `/tiprr-favicon-v2.png`.
- Stable logo sizing and stronger empty-state contrast are defined in `frontend/src/mascot.css`. Backend, authentication and financial behavior are unchanged.

## Pixel wordmark rebrand — 2026-10-03

- Latest user requirement: “Ganti bro pake ini jangan robot mascot lagi” and remove the extra upper-left Tiprr text so it does not overlap the logo. Selected “Pixel clean: logo asli, judul pixel, tombol bersudut tegas, aksen hitam-putih; isi tetap mudah dibaca.” Explicitly: “Hanya ubah nuansa nya menjadi pixel isi tetap pertahankan.”
- Supersedes ALL previous robot/mascot design decisions. Use the user's supplied original pixel Tiprr wordmark, not a generated or redrawn logo. Source: `https://customer-assets-jai6qajn.emergentagent.net/job_bonk-sender/artifacts/tf10yojk_file_000000006e1481faafb8aad5d292133d.png`.
- Original saved in `frontend/public/tiprr-logo-original.png`. Prepared `tiprr-logo-pixel.png` by removing only connected exterior black background and trimming padding; enclosed black lettering and original gray/white pixel artwork preserved. `tiprr-logo-icon.png` is the favicon and touch icon.
- Shared `BrandImage` replaces the Bot image component in home, demo avatar, footer, and all empty states. `Brand` contains the image only, with accessible link label and NO duplicate visible text. Workspace mobile header also uses the same image-only Brand. No robot is rendered in any current UI.
- `frontend/src/pixel-theme.css` is the visual-only theme layer imported after App.css. Pixelify Sans headings, square edges, restrained offset shadows, grayscale branding; DM Sans body/form/balance text remains readable. Existing site copy, routes, animated command demo, forms and backend behavior retained unchanged.
- Removed superseded `mascot.css`. Some unused older CSS selectors in App.css and archived robot files remain inert; do not reintroduce them in UI.
- Verification: frontend build succeeds with only existing upstream Solana SDK source-map warnings. Desktop1920x800 and mobile390x844/320x800: no horizontal overflow or branding overlap. Header branding has no text node; all logo images and favicon return/load successfully. X dialog, wallet dialog, navigation and demo SOL/BONK/USDC/pause/replay regression checks pass. See `test_reports/iteration_3.json`.
- QA noted expected HTTP401 from existing signed-out `/api/me` session checks. These are intentional server authorization responses, caught by AppContext with no application error logging or broken UI; not a rebrand regression. Kept authentication behavior unchanged per the user's style-only scope.
- Next visual task is user feedback only; no content or financial feature changes requested in this phase. Prior production integration backlog remains as documented above.

## Next session handoff (continued)

## Smoother logo + mobile header/footer fix — 2026-10-03

- User provided newer, smoother artwork and requested balanced (not oversized/tiny) mobile top-left branding plus removal of the duplicated logo in the very bottom footer. Confirmed: keep the CTA logo beside “Make someone’s timeline a little better”; delete only the logo in the footer below it.
- Latest approved source: `https://customer-assets-jai6qajn.emergentagent.net/job_bonk-sender/artifacts/ej4qpsyn_file_00000000458481faa7d09ab1401e8c2c.png`. Supersedes the previous pixel logo artwork, not the pixel-clean website styling.
- Assets: original saved as `tiprr-logo-smooth-original.png`; connected exterior background removal produces transparent `tiprr-logo-smooth.png` (1183x595), preserving all original interior black/white/gray art. `tiprr-logo-smooth-icon.png` used for favicon and touch icon. Shared BrandImage updates every visible logo; no redraw or robotic mascot.
- Home and workspace mobile headers now70px tall; logos80x42px at320/360px viewport widths,84x44px at390/430px widths. Image remains contained and smoothly resampled. Desktop sizing unchanged.
- Removed Brand from final `.site-footer`; retained message + status link and centered these on mobile. `bottom-cta-logo` remains exactly once above footer. Existing content, animations, pixel theme, financial/auth/backend flows unchanged.
- Independent required bugfix verification PASSED: `test_reports/iteration_4.json`, no remaining issues. Verified exact mobile dimensions, no overlap/overflow/duplicate text, all current logo assets load, zero footer images/brand links, exactly one CTA logo, and working top brand/footer status/login dialog interactions. Screenshot evidence under `test_reports/screens_rebrand_iter5/`.
- No next tasks required for this visual fix. Existing devnet/X/claims/UsePaid production limitations/backlog remain unchanged.

## Current handoff

Read TIPRR_SETUP.md, this PRD and test_reports/iteration_2.json first. Do not call the app a production-ready bot. Do not enable X from env values alone: identity + worker phase remains unimplemented. Do not accept arbitrary manual treasury deposits as credited. Keep the provided environment URLs and Mongo URI intact. Test accounts use ephemeral generated keys; there is intentionally no shared wallet private key in test_credentials.md.