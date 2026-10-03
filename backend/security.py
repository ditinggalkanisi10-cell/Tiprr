import base64
import hashlib
import os
import secrets
from datetime import timedelta
from fastapi import HTTPException, Request
from nacl.signing import VerifyKey
from solders.pubkey import Pubkey
from core import db, now


def address(value: str):
    try:
        key = Pubkey.from_string(value)
        if not key.is_on_curve():
            raise ValueError()
        return key
    except Exception:
        raise HTTPException(422, 'Enter a valid Solana wallet address (not a token account).')


async def limit(key: str, maximum=60, seconds=60):
    bucket = int(now().timestamp()) // seconds
    doc = await db.rate_limits.find_one_and_update(
        {'_id': f'{key}:{bucket}'},
        {'$inc': {'count': 1}, '$setOnInsert': {'expires_at': now() + timedelta(seconds=seconds * 2)}},
        upsert=True, return_document=True, projection={'_id': 0})
    if doc['count'] > maximum:
        raise HTTPException(429, 'Too many requests. Please try again shortly.')


async def current_user(request: Request):
    token = request.cookies.get('tiprr_session')
    if not token:
        raise HTTPException(401, 'Connect and verify your wallet first.')
    session = await db.sessions.find_one({
        'token_hash': hashlib.sha256(token.encode()).hexdigest(), 'expires_at': {'$gt': now()}
    }, {'_id': 0})
    if not session:
        raise HTTPException(401, 'Your session has expired. Reconnect your wallet.')
    # Do not rely on SameSite: an embedding proxy may rewrite cookie attributes.
    # This session-bound token is only readable through same-origin/CORS-allowed JSON.
    if request.method not in ['GET', 'HEAD', 'OPTIONS']:
        supplied = request.headers.get('x-csrf-token', '')
        if not session.get('csrf_token') or not secrets.compare_digest(supplied, session['csrf_token']):
            raise HTTPException(403, 'CSRF verification failed. Refresh your session and try again.')
    request.state.csrf_token = session.get('csrf_token')
    user = await db.users.find_one({'id': session['user_id']}, {'_id': 0})
    if not user:
        raise HTTPException(401, 'Account not found.')
    return user


def verify_signature(wallet, message, signature):
    try:
        VerifyKey(bytes(address(wallet))).verify(message.encode(), base64.b64decode(signature, validate=True))
    except Exception:
        raise HTTPException(401, 'Wallet signature is invalid.')


def cron_authorized(request: Request):
    secret = os.environ.get('WEBHOOK_CRON_SECRET')
    if not secret or not secrets.compare_digest(request.headers.get('authorization', ''), f'Bearer {secret}'):
        raise HTTPException(401, 'Unauthorized worker request.')


async def admin_user(request: Request):
    user = await current_user(request)
    allowed = [x.strip() for x in os.environ.get('ADMIN_WALLETS', '').split(',') if x.strip()]
    if user['wallet'] not in allowed:
        raise HTTPException(403, 'Administrator access is required.')
    return user
