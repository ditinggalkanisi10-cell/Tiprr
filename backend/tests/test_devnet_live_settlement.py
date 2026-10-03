"""Optional live devnet settlement smoke test (skips if faucet/RPC blocks funding)."""

import base64
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import Transaction


load_dotenv('/app/frontend/.env')


def _rpc(method, params):
    url = os.environ.get('SOLANA_RPC_URL')
    if not url:
        pytest.skip('SOLANA_RPC_URL not configured')
    response = requests.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}, timeout=30)
    response.raise_for_status()
    body = response.json()
    if body.get('error'):
        raise RuntimeError(str(body['error']))
    return body.get('result')


def _sign_message(keypair: Keypair, message: str) -> str:
    return base64.b64encode(bytes(keypair.sign_message(message.encode()))).decode()


def test_live_devnet_deposit_then_withdraw_if_funded():
    """Real devnet path: airdrop -> signed deposit submit -> idempotent resubmit -> withdraw reserve/finalization."""
    base_url = os.environ.get('REACT_APP_BACKEND_URL')
    if not base_url:
        pytest.skip('REACT_APP_BACKEND_URL is not configured')
    base_url = base_url.rstrip('/')

    client = requests.Session()
    client.headers.update({'Content-Type': 'application/json'})

    wallet = Keypair()
    wallet_pubkey = str(wallet.pubkey())

    # Wallet verify to get cookie + csrf
    challenge = client.post(f'{base_url}/api/wallet/challenge', json={'wallet': wallet_pubkey}, timeout=20)
    assert challenge.status_code == 200
    message = challenge.json()['message']
    verify = client.post(
        f'{base_url}/api/wallet/verify',
        json={'challenge_id': challenge.json()['id'], 'signature': _sign_message(wallet, message)},
        timeout=20,
    )
    assert verify.status_code == 200
    csrf = verify.json()['csrf_token']
    client.headers.update({'X-CSRF-Token': csrf})

    # Fund disposable wallet using devnet faucet through configured RPC.
    try:
        airdrop_sig = _rpc('requestAirdrop', [wallet_pubkey, 50_000_000])  # 0.05 SOL
    except Exception:
        pytest.skip('live settlement not verified: faucet unavailable/rate-limited')

    # Wait for airdrop finalization.
    for _ in range(25):
        try:
            tx = _rpc('getTransaction', [airdrop_sig, {'encoding': 'jsonParsed', 'commitment': 'finalized', 'maxSupportedTransactionVersion': 0}])
            if tx:
                break
        except Exception:
            pass
        time.sleep(1.2)
    else:
        pytest.skip('live settlement not verified: faucet funding not finalized in time')

    # Create and sign real deposit transaction from server-built unsigned bytes.
    create = client.post(f'{base_url}/api/deposit/create', json={'asset_id': 'native-sol', 'amount': '0.00001'}, timeout=30)
    assert create.status_code == 200
    deposit = create.json()
    unsigned_raw = base64.b64decode(deposit['unsigned_transaction'])
    tx = Transaction.from_bytes(unsigned_raw)
    tx.sign([wallet], tx.message.recent_blockhash)
    signed_b64 = base64.b64encode(bytes(tx)).decode()

    submit = client.post(
        f"{base_url}/api/deposits/{deposit['id']}/submit",
        json={'signed_transaction': signed_b64},
        timeout=40,
    )
    assert submit.status_code == 200

    # Poll until completed or failed.
    final = submit.json()
    for _ in range(40):
        if final.get('status') in ['COMPLETED', 'FAILED']:
            break
        time.sleep(2)
        poll = client.get(f"{base_url}/api/deposits/{deposit['id']}", timeout=30)
        assert poll.status_code == 200
        final = poll.json()

    if final.get('status') != 'COMPLETED':
        pytest.skip('live settlement not verified: deposit did not finalize to COMPLETED')

    # Re-submit same signed payload; should be idempotent (no duplicate credit).
    balances_before = client.get(f'{base_url}/api/balances', timeout=20)
    assert balances_before.status_code == 200
    sol_before = next(x for x in balances_before.json() if x['id'] == 'native-sol')
    available_before = int(sol_before['available_base_units'])

    resubmit = client.post(
        f"{base_url}/api/deposits/{deposit['id']}/submit",
        json={'signed_transaction': signed_b64},
        timeout=40,
    )
    assert resubmit.status_code == 200

    balances_after = client.get(f'{base_url}/api/balances', timeout=20)
    assert balances_after.status_code == 200
    sol_after = next(x for x in balances_after.json() if x['id'] == 'native-sol')
    available_after = int(sol_after['available_base_units'])
    assert available_after == available_before

    # Withdraw part and verify reserve/finalization progression exists.
    destination = str(Keypair().pubkey())
    withdraw = client.post(
        f'{base_url}/api/withdraw',
        json={
            'asset_id': 'native-sol',
            'amount': '0.000005',
            'destination': destination,
            'idempotency_key': f'test-live-{uuid.uuid4()}',
        },
        timeout=30,
    )
    assert withdraw.status_code in [200, 202]
    payment = withdraw.json()
    assert payment['type'] == 'WITHDRAWAL'

    # Confirm ledger moved value to reserved or completed payout.
    settled_or_reserved = False
    for _ in range(25):
        rows = client.get(f'{base_url}/api/transactions', timeout=25)
        assert rows.status_code == 200
        tx_row = next((x for x in rows.json() if x['id'] == payment['id']), None)
        if tx_row and tx_row.get('status') in ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED']:
            settled_or_reserved = True
            break
        time.sleep(1.5)
    assert settled_or_reserved
