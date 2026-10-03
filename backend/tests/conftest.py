import base64
import os
import time
import hashlib

import pytest
import requests
from dotenv import load_dotenv
from solders.keypair import Keypair


load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')


@pytest.fixture(scope='session')
def base_url():
    value = os.environ.get('REACT_APP_BACKEND_URL')
    if not value:
        pytest.skip('REACT_APP_BACKEND_URL is not configured')
    return value.rstrip('/')


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    return session


def _sign_message(keypair: Keypair, message: str) -> str:
    signature = keypair.sign_message(message.encode())
    return base64.b64encode(bytes(signature)).decode()


@pytest.fixture
def wallet_session(api_client, base_url):
    """Wallet auth flow fixture for /wallet/challenge + /wallet/verify."""
    keypair = Keypair()
    wallet = str(keypair.pubkey())

    challenge = api_client.post(f'{base_url}/api/wallet/challenge', json={'wallet': wallet})
    assert challenge.status_code == 200
    body = challenge.json()
    signature_b64 = _sign_message(keypair, body['message'])

    verify = api_client.post(
        f'{base_url}/api/wallet/verify',
        json={'challenge_id': body['id'], 'signature': signature_b64},
    )
    assert verify.status_code == 200

    set_cookie = verify.headers.get('set-cookie', '').lower()
    assert 'tiprr_session=' in set_cookie
    assert 'secure' in set_cookie
    assert 'httponly' in set_cookie

    user = verify.json()
    csrf_token = user.get('csrf_token')
    assert isinstance(csrf_token, str)
    assert len(csrf_token) > 10
    api_client.headers.update({'X-CSRF-Token': csrf_token})

    yield {
        'client': api_client,
        'keypair': keypair,
        'wallet': wallet,
        'user': user,
        'csrf_token': csrf_token,
        'sign_message': lambda msg: _sign_message(keypair, msg),
    }

    # Best-effort authenticated logout first.
    api_client.post(f'{base_url}/api/auth/logout')

    # Safe cleanup for disposable test wallet/session data only.
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    if mongo_url and db_name:
        from pymongo import MongoClient
        mongo = MongoClient(mongo_url)
        db = mongo[db_name]
        try:
            user_id = user.get('id')
            wallet_addr = user.get('wallet')
            token = api_client.cookies.get('tiprr_session')
            if token:
                db.sessions.delete_many({'token_hash': hashlib.sha256(token.encode()).hexdigest()})
            if user_id:
                db.sessions.delete_many({'user_id': user_id})
                db.vaults.delete_many({'user_id': user_id})
                db.deposits.delete_many({'user_id': user_id})
                db.payments.delete_many({'user_id': user_id})
                db.audit_logs.delete_many({'user_id': user_id})
                db.users.delete_many({'id': user_id})
            if wallet_addr:
                db.challenges.delete_many({'wallet': wallet_addr})
        finally:
            mongo.close()

    time.sleep(0.05)
