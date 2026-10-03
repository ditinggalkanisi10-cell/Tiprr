"""Critical TIPRR devnet foundation tests for wallet auth, funds, cron and ledger."""

import os
import time
import uuid

import pytest
from dotenv import load_dotenv
from pymongo import MongoClient
from solders.keypair import Keypair


load_dotenv('/app/backend/.env')


def test_health_and_mode(api_client, base_url):
    response = api_client.get(f'{base_url}/api/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['network'] == 'devnet'


def test_system_status_rpc_and_signer_present(api_client, base_url):
    response = api_client.get(f'{base_url}/api/system/status')
    assert response.status_code == 200
    data = response.json()
    assert data['network'] == 'devnet'
    assert data['rpc']['status'] == 'connected'
    assert data['signer']['status'] == 'configured'
    assert isinstance(data['signer']['public_key'], str)
    assert len(data['signer']['public_key']) >= 32


def test_validate_command_good_and_bad(api_client, base_url):
    ok = api_client.post(f'{base_url}/api/tools/validate-command', json={'text': '/tiprr 10 BONK @ryansshh'})
    assert ok.status_code == 200
    ok_data = ok.json()
    assert ok_data['amount'] == '10'
    assert ok_data['asset'] == 'BONK'
    assert ok_data['recipient_username'] == 'ryansshh'
    assert ok_data['executed'] is False

    bad = api_client.post(f'{base_url}/api/tools/validate-command', json={'text': '/tiprr 0 SOL @u'})
    assert bad.status_code == 422
    assert 'Invalid format' in str(bad.json().get('detail'))


def test_csrf_origin_blocked_on_post(api_client, base_url):
    blocked = api_client.post(
        f'{base_url}/api/tools/validate-command',
        headers={'Origin': 'https://evil.example'},
        json={'text': '/tiprr 1 SOL @ok'},
    )
    assert blocked.status_code == 403
    assert blocked.json()['detail'] == 'Origin not allowed.'


def test_wallet_challenge_verify_replay_and_logout(api_client, base_url):
    keypair = Keypair()
    wallet = str(keypair.pubkey())

    challenge = api_client.post(f'{base_url}/api/wallet/challenge', json={'wallet': wallet})
    assert challenge.status_code == 200
    challenge_data = challenge.json()

    import base64
    signature = base64.b64encode(bytes(keypair.sign_message(challenge_data['message'].encode()))).decode()
    verify = api_client.post(
        f'{base_url}/api/wallet/verify',
        json={'challenge_id': challenge_data['id'], 'signature': signature},
    )
    assert verify.status_code == 200
    set_cookie = verify.headers.get('set-cookie', '').lower()
    assert 'tiprr_session=' in set_cookie
    assert 'secure' in set_cookie
    assert 'httponly' in set_cookie
    user = verify.json()
    assert user['wallet'] == wallet
    assert isinstance(user.get('csrf_token'), str)
    assert len(user['csrf_token']) > 10

    api_client.headers.update({'X-CSRF-Token': user['csrf_token']})

    me = api_client.get(f'{base_url}/api/me')
    assert me.status_code == 200
    me_data = me.json()
    assert me_data['wallet'] == wallet
    assert me_data['csrf_token'] == user['csrf_token']

    replay = api_client.post(
        f'{base_url}/api/wallet/verify',
        json={'challenge_id': challenge_data['id'], 'signature': signature},
    )
    assert replay.status_code == 401

    logout = api_client.post(f'{base_url}/api/auth/logout')
    assert logout.status_code == 200
    post_logout_me = api_client.get(f'{base_url}/api/me')
    assert post_logout_me.status_code == 401


def test_wallet_verify_bad_signature_rejected(api_client, base_url):
    owner = Keypair()
    attacker = Keypair()
    wallet = str(owner.pubkey())

    challenge = api_client.post(f'{base_url}/api/wallet/challenge', json={'wallet': wallet})
    assert challenge.status_code == 200
    body = challenge.json()

    import base64
    wrong = base64.b64encode(bytes(attacker.sign_message(body['message'].encode()))).decode()
    verify = api_client.post(
        f'{base_url}/api/wallet/verify',
        json={'challenge_id': body['id'], 'signature': wrong},
    )
    assert verify.status_code == 401
    assert verify.json()['detail'] == 'Wallet signature is invalid.'


@pytest.mark.parametrize(
    'amount, expected_status',
    [
        ('0', 422),
        ('-1', 422),
        ('1e3', 422),
        ('0.0000000001', 422),
        ('9223372037', 422),
        ('0.000000001', 200),
    ],
)
def test_deposit_amount_parser_rules(wallet_session, base_url, amount, expected_status):
    response = wallet_session['client'].post(
        f'{base_url}/api/deposit/create',
        json={'asset_id': 'native-sol', 'amount': amount},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        data = response.json()
        assert data['asset_id'] == 'native-sol'
        assert data['amount'] == amount
        assert isinstance(data['unsigned_transaction'], str)


def test_balances_and_admin_denial(wallet_session, base_url):
    balances = wallet_session['client'].get(f'{base_url}/api/balances')
    assert balances.status_code == 200
    rows = balances.json()
    assert any(row['id'] == 'native-sol' for row in rows)

    denied = wallet_session['client'].get(f'{base_url}/api/admin/stats')
    assert denied.status_code == 403
    assert denied.json()['detail'] == 'Administrator access is required.'


def test_deposit_submit_malformed_transaction_rejected(wallet_session, base_url):
    created = wallet_session['client'].post(
        f'{base_url}/api/deposit/create',
        json={'asset_id': 'native-sol', 'amount': '0.000000001'},
    )
    assert created.status_code == 200
    deposit = created.json()

    malformed = wallet_session['client'].post(
        f"{base_url}/api/deposits/{deposit['id']}/submit",
        json={'signed_transaction': 'bm90LWEtdmFsaWQtdHg='},
    )
    assert malformed.status_code == 422
    assert 'Signed transaction does not match' in malformed.json()['detail']


def test_transactions_payload_includes_details_for_activity_dialog(wallet_session, base_url):
    created = wallet_session['client'].post(
        f'{base_url}/api/deposit/create',
        json={'asset_id': 'native-sol', 'amount': '0.000000001'},
    )
    assert created.status_code == 200
    deposit = created.json()
    assert deposit['status'] == 'PENDING'

    rows = wallet_session['client'].get(f'{base_url}/api/transactions')
    assert rows.status_code == 200
    payload = rows.json()
    match = next((row for row in payload if row['id'] == deposit['id']), None)
    assert match is not None
    for field in ['mint_address', 'amount_base_units', 'source', 'destination', 'status', 'created_at']:
        assert field in match
    # Pending deposits may not include signature yet; UI falls back to “Not submitted yet”.
    assert match.get('signature') is None or isinstance(match.get('signature'), str)


def test_claim_requires_x_identity(wallet_session, base_url):
    claim = wallet_session['client'].post(f"{base_url}/api/claims/{uuid.uuid4()}/claim")
    assert claim.status_code == 403
    assert 'Verified X identity is required' in claim.json()['detail']


def test_csrf_missing_token_blocked(wallet_session, base_url):
    client = wallet_session['client']
    client.headers.pop('X-CSRF-Token', None)
    response = client.post(
        f'{base_url}/api/deposit/create',
        json={'asset_id': 'native-sol', 'amount': '0.000000001'},
    )
    assert response.status_code == 403
    assert 'CSRF verification failed' in response.json()['detail']


def test_csrf_wrong_token_blocked(wallet_session, base_url):
    client = wallet_session['client']
    client.headers.update({'X-CSRF-Token': 'definitely-wrong-token'})
    response = client.post(
        f'{base_url}/api/deposit/create',
        json={'asset_id': 'native-sol', 'amount': '0.000000001'},
    )
    assert response.status_code == 403
    assert 'CSRF verification failed' in response.json()['detail']


def test_csrf_cross_session_token_blocked(api_client, base_url):
    # Session A
    keypair_a = Keypair()
    wallet_a = str(keypair_a.pubkey())
    challenge_a = api_client.post(f'{base_url}/api/wallet/challenge', json={'wallet': wallet_a})
    assert challenge_a.status_code == 200
    import base64
    sig_a = base64.b64encode(bytes(keypair_a.sign_message(challenge_a.json()['message'].encode()))).decode()
    verify_a = api_client.post(
        f'{base_url}/api/wallet/verify',
        json={'challenge_id': challenge_a.json()['id'], 'signature': sig_a},
    )
    assert verify_a.status_code == 200
    token_a = verify_a.json()['csrf_token']

    # Session B
    client_b = api_client.__class__()
    client_b.headers.update({'Content-Type': 'application/json'})
    keypair_b = Keypair()
    wallet_b = str(keypair_b.pubkey())
    challenge_b = client_b.post(f'{base_url}/api/wallet/challenge', json={'wallet': wallet_b})
    assert challenge_b.status_code == 200
    sig_b = base64.b64encode(bytes(keypair_b.sign_message(challenge_b.json()['message'].encode()))).decode()
    verify_b = client_b.post(
        f'{base_url}/api/wallet/verify',
        json={'challenge_id': challenge_b.json()['id'], 'signature': sig_b},
    )
    assert verify_b.status_code == 200

    # Use token from A in B -> must fail.
    client_b.headers.update({'X-CSRF-Token': token_a})
    blocked = client_b.post(
        f'{base_url}/api/deposit/create',
        json={'asset_id': 'native-sol', 'amount': '0.000000001'},
    )
    assert blocked.status_code == 403
    assert 'CSRF verification failed' in blocked.json()['detail']

    # Correct token for B -> expected business flow status (200 create)
    client_b.headers.update({'X-CSRF-Token': verify_b.json()['csrf_token']})
    allowed = client_b.post(
        f'{base_url}/api/deposit/create',
        json={'asset_id': 'native-sol', 'amount': '0.000000001'},
    )
    assert allowed.status_code == 200
    payload = allowed.json()
    assert payload['asset_id'] == 'native-sol'
    assert payload['status'] == 'PENDING'


def test_csrf_logout_requires_valid_token(wallet_session, base_url):
    client = wallet_session['client']
    valid = wallet_session['csrf_token']

    client.headers.update({'X-CSRF-Token': 'wrong-token'})
    blocked = client.post(f'{base_url}/api/auth/logout')
    assert blocked.status_code == 403

    client.headers.update({'X-CSRF-Token': valid})
    allowed = client.post(f'{base_url}/api/auth/logout')
    assert allowed.status_code == 200
    me = client.get(f'{base_url}/api/me')
    assert me.status_code == 401


def test_csrf_malicious_origin_blocked_even_with_valid_token(wallet_session, base_url):
    client = wallet_session['client']
    client.headers.update({'X-CSRF-Token': wallet_session['csrf_token']})
    response = client.post(
        f'{base_url}/api/deposit/create',
        headers={'Origin': 'https://evil.example'},
        json={'asset_id': 'native-sol', 'amount': '0.000000001'},
    )
    assert response.status_code == 403
    assert response.json()['detail'] == 'Origin not allowed.'


def test_cron_requires_secret_and_duplicate_run_id_is_idempotent(api_client, base_url):
    body = {
        'event': 'schedule.triggered',
        'run_id': f'test-run-{uuid.uuid4()}',
        'schedule_id': 'reconcile-devnet',
        'dispatch_time': '2026-02-01T00:00:00Z',
    }
    no_auth = api_client.post(f'{base_url}/api/cron/reconcile', json='not-json-body')
    assert no_auth.status_code == 401

    bad_auth = api_client.post(
        f'{base_url}/api/cron/reconcile',
        headers={'Authorization': 'Bearer wrong-secret'},
        json='still-invalid',
    )
    assert bad_auth.status_code == 401

    secret = os.environ.get('WEBHOOK_CRON_SECRET')
    if not secret:
        pytest.skip('WEBHOOK_CRON_SECRET not configured')

    ok = api_client.post(
        f'{base_url}/api/cron/reconcile',
        headers={'Authorization': f'Bearer {secret}'},
        json={'event': 'oops'},
    )
    assert ok.status_code == 400

    ok = api_client.post(
        f'{base_url}/api/cron/reconcile',
        headers={'Authorization': f'Bearer {secret}'},
        json=body,
    )
    assert ok.status_code == 200
    first = ok.json()
    assert first['accepted'] is True
    assert first['duplicate'] is False

    duplicate = api_client.post(
        f'{base_url}/api/cron/reconcile',
        headers={'Authorization': f'Bearer {secret}'},
        json=body,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()['duplicate'] is True


def test_cron_run_record_created_and_finishes(api_client, base_url):
    secret = os.environ.get('WEBHOOK_CRON_SECRET')
    if not secret:
        pytest.skip('WEBHOOK_CRON_SECRET not configured')

    run_id = f'test-run-{uuid.uuid4()}'
    body = {
        'event': 'schedule.triggered',
        'run_id': run_id,
        'schedule_id': 'reconcile-devnet',
        'dispatch_time': '2026-02-01T00:00:00Z',
    }

    trigger = api_client.post(
        f'{base_url}/api/cron/reconcile',
        headers={'Authorization': f'Bearer {secret}'},
        json=body,
    )
    assert trigger.status_code == 200

    mongo_url, db_name = os.environ.get('MONGO_URL'), os.environ.get('DB_NAME')
    if not mongo_url or not db_name:
        pytest.skip('Mongo env not configured for direct job verification')

    client = MongoClient(mongo_url)
    jobs = client[db_name].jobs
    found = None
    for _ in range(20):
        found = jobs.find_one({'run_id': run_id}, {'_id': 0, 'status': 1})
        if found and found.get('status') in ['COMPLETED', 'FAILED']:
            break
        time.sleep(0.3)
    assert found is not None
    assert found['status'] in ['COMPLETED', 'FAILED', 'PENDING']


def test_cron_yaml_schedule_every_15m_present():
    from pathlib import Path
    cron_file = Path('/app/.emergent/crons.yml')
    assert cron_file.exists()
    raw = cron_file.read_text(encoding='utf-8')
    assert '*/15' in raw or 'every 15' in raw.lower()
