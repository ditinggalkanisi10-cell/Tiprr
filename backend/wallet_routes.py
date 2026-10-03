import hashlib
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from core import db, now, uid, Document
from security import current_user, verify_signature, address, limit
import os

router = APIRouter(prefix='/api')


class ChallengeRequest(BaseModel):
    wallet: str = Field(min_length=32, max_length=44)


class VerifyRequest(BaseModel):
    challenge_id: str = Field(max_length=50)
    signature: str = Field(max_length=100)


@router.post('/wallet/challenge', response_model=Document)
async def challenge(body: ChallengeRequest, request: Request):
    await limit(f'challenge:{request.client.host}', 20)
    address(body.wallet)
    nonce = secrets.token_urlsafe(32)
    challenge_id = uid()
    message = (f"{os.environ['APP_ORIGIN']}\nTIPRR wallet ownership verification\n"
               f'Wallet: {body.wallet}\nNetwork: devnet\nNonce: {nonce}\n'
               f'Issued at: {now().isoformat()}\nExpires in 5 minutes.\n'
               'This signature does not authorize a transaction. No real funds.')
    await db.challenges.insert_one({'id': challenge_id, 'wallet': body.wallet, 'message': message,
                                    'used': False, 'expires_at': now() + timedelta(minutes=5)})
    return {'id': challenge_id, 'message': message}


@router.post('/wallet/verify', response_model=Document)
async def verify(body: VerifyRequest, request: Request, response: Response):
    await limit(f'verify:{request.client.host}', 30)
    doc = await db.challenges.find_one({'id': body.challenge_id, 'used': False,
                                       'expires_at': {'$gt': now()}}, {'_id': 0})
    if not doc:
        raise HTTPException(401, 'Challenge expired or already used.')
    verify_signature(doc['wallet'], doc['message'], body.signature)
    consumed = await db.challenges.update_one({'id': body.challenge_id, 'used': False}, {'$set': {'used': True}})
    if not consumed.modified_count:
        raise HTTPException(401, 'Challenge already used.')
    user_id = uid()
    try:
        await db.users.update_one({'wallet': doc['wallet']}, {'$setOnInsert': {
            'id': user_id, 'wallet': doc['wallet'], 'x_user_id': None, 'username': None,
            'display_name': None, 'created_at': now().isoformat(),
        }, '$set': {'updated_at': now().isoformat()}}, upsert=True)
    except DuplicateKeyError:
        pass
    user = await db.users.find_one({'wallet': doc['wallet']}, {'_id': 0})
    await db.vaults.update_one({'user_id': user['id']}, {'$setOnInsert': {'balances': {}, 'journal': []}}, upsert=True)
    token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({'token_hash': hashlib.sha256(token.encode()).hexdigest(),
                                  'user_id': user['id'], 'csrf_token': csrf_token,
                                  'expires_at': now() + timedelta(hours=12)})
    response.set_cookie('tiprr_session', token, max_age=43200, httponly=True, secure=True, samesite='strict', path='/api')
    await db.audit_logs.insert_one({'id': uid(), 'user_id': user['id'], 'action': 'wallet_verified', 'created_at': now().isoformat()})
    return {**user, 'csrf_token': csrf_token}


@router.get('/me', response_model=Document)
@router.get('/profile', response_model=Document)
async def me(request: Request, user=Depends(current_user)):
    return {**user, 'auth_type': 'verified_devnet_wallet', 'x_connected': bool(user.get('x_user_id')),
            'csrf_token': request.state.csrf_token}


@router.post('/auth/logout')
async def logout(request: Request, response: Response, user=Depends(current_user)):
    token = request.cookies.get('tiprr_session', '')
    await db.sessions.delete_one({'token_hash': hashlib.sha256(token.encode()).hexdigest()})
    response.delete_cookie('tiprr_session', path='/api', secure=True, httponly=True, samesite='strict')
    return {'ok': True}


@router.get('/auth/x/start')
@router.post('/auth/x/callback')
async def x_not_configured():
    raise HTTPException(503, {'message': 'X authentication is not enabled in this devnet build.',
        'required': ['X_CLIENT_ID', 'X_CLIENT_SECRET', 'X_REDIRECT_URI'],
        'next_step': 'Configure official X OAuth 2.0 PKCE in the next integration phase.'})
