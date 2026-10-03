import os
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from core import db, uid, now, Document
from security import current_user, address, limit
from amounts import to_units, display_units
from chain import resolve_mint, signer, build_transaction, verify_signed, rpc
from payment_service import process_payment, reconcile_deposit, PUBLIC_PROJECTION

router = APIRouter(prefix='/api')


class MintRequest(BaseModel):
    mint_address: str = Field(min_length=32, max_length=44)


class DepositRequest(BaseModel):
    asset_id: str = Field(max_length=50)
    amount: str = Field(max_length=40)


class SubmitRequest(BaseModel):
    signed_transaction: str = Field(max_length=2000)


class WithdrawRequest(DepositRequest):
    destination: str = Field(min_length=32, max_length=44)
    idempotency_key: str = Field(min_length=16, max_length=80, pattern=r'^[a-zA-Z0-9-]+$')


async def asset_by_id(asset_id):
    asset = await db.tokens.find_one({'id': asset_id}, {'_id': 0})
    if not asset:
        raise HTTPException(404, 'Asset not found. Add its devnet mint first.')
    return asset


@router.get('/tokens', response_model=list[Document])
async def tokens():
    return await db.tokens.find({}, {'_id': 0}).sort('created_at', 1).to_list(500)


@router.post('/tokens/resolve', response_model=Document)
async def add_token(body: MintRequest, user=Depends(current_user)):
    await limit(f'mint:{user["id"]}', 10)
    asset = await resolve_mint(body.mint_address)
    try:
        await db.tokens.update_one({'mint_address': body.mint_address}, {'$setOnInsert': {
            **asset, 'id': uid(), 'created_at': now().isoformat()}}, upsert=True)
    except DuplicateKeyError:
        pass  # Another verified request registered this same canonical mint.
    return await db.tokens.find_one({'mint_address': body.mint_address}, {'_id': 0})


@router.get('/balances', response_model=list[Document])
async def balances(user=Depends(current_user)):
    vault = await db.vaults.find_one({'user_id': user['id']}, {'_id': 0, 'balances': 1})
    result = []
    for asset in await db.tokens.find({}, {'_id': 0}).to_list(500):
        value = (vault or {}).get('balances', {}).get(asset['id'], {})
        available, reserved = value.get('available', 0), value.get('reserved', 0)
        result.append({**asset, 'available': display_units(available, asset['decimals']),
                       'reserved': display_units(reserved, asset['decimals']),
                       'available_base_units': str(available), 'reserved_base_units': str(reserved)})
    return result


@router.post('/deposit/create', response_model=Document)
async def create_deposit(body: DepositRequest, user=Depends(current_user)):
    await limit(f'deposit:{user["id"]}', 10)
    asset = await asset_by_id(body.asset_id)
    amount = to_units(body.amount, asset['decimals'])
    deposit_id = uid()
    destination = str(signer().pubkey())
    built = await build_transaction(asset, amount, user['wallet'], destination, deposit_id)
    doc = {'id': deposit_id, 'user_id': user['id'], 'asset_id': asset['id'], 'symbol': asset['symbol'],
           'mint_address': asset['mint_address'], 'amount': body.amount, 'amount_base_units': str(amount),
           'source': user['wallet'], 'destination': destination, 'status': 'PENDING', 'type': 'DEPOSIT',
           'network': 'devnet', 'created_at': now().isoformat(), 'message': built['message'],
           'unsigned_transaction': built['transaction'], 'last_valid_block_height': built['last_valid_block_height']}
    await db.deposits.insert_one(doc.copy())
    return {k: v for k, v in doc.items() if k != 'message'}


@router.post('/deposits/{deposit_id}/submit', response_model=Document)
async def submit_deposit(deposit_id: str, body: SubmitRequest, user=Depends(current_user)):
    deposit = await db.deposits.find_one({'id': deposit_id, 'user_id': user['id']}, {'_id': 0})
    if not deposit:
        raise HTTPException(404, 'Deposit not found.')
    signature = verify_signed(body.signed_transaction, deposit['message'], user['wallet'])
    if deposit.get('signature') and deposit['signature'] != signature:
        raise HTTPException(409, 'A different transaction is already associated with this deposit.')
    if deposit['status'] in ['COMPLETED', 'FAILED']:
        return await db.deposits.find_one({'id': deposit_id}, PUBLIC_PROJECTION)
    try:
        await db.deposits.update_one({'id': deposit_id, 'status': 'PENDING'}, {'$set': {
            'signature': signature, 'signed_transaction': body.signed_transaction, 'status': 'PROCESSING'}})
    except DuplicateKeyError:
        raise HTTPException(409, 'This blockchain transaction has already been registered.')
    try:
        await rpc('sendTransaction', [body.signed_transaction, {'encoding': 'base64', 'skipPreflight': False,
                    'preflightCommitment': 'finalized', 'maxRetries': 0}])
        await reconcile_deposit({**deposit, 'signature': signature, 'status': 'PROCESSING'})
    except HTTPException as error:
        await db.deposits.update_one({'id': deposit_id}, {'$set': {'error': str(error.detail)}})
    return await db.deposits.find_one({'id': deposit_id}, PUBLIC_PROJECTION)


@router.get('/deposits/{deposit_id}', response_model=Document)
async def deposit_status(deposit_id: str, user=Depends(current_user)):
    deposit = await db.deposits.find_one({'id': deposit_id, 'user_id': user['id']}, {'_id': 0})
    if not deposit:
        raise HTTPException(404, 'Deposit not found.')
    await reconcile_deposit(deposit)
    return await db.deposits.find_one({'id': deposit_id}, PUBLIC_PROJECTION)


@router.post('/withdraw', response_model=Document, status_code=202)
async def withdraw(body: WithdrawRequest, background: BackgroundTasks, user=Depends(current_user)):
    await limit(f'withdraw:{user["id"]}', 10, 3600)
    existing = await db.payments.find_one({'user_id': user['id'], 'idempotency_key': body.idempotency_key}, PUBLIC_PROJECTION)
    if existing:
        if any(existing[field] != value for field, value in [('asset_id', body.asset_id), ('amount', body.amount), ('destination', body.destination)]):
            raise HTTPException(409, 'Idempotency key already used with different payment details.')
        return existing
    address(body.destination)
    if body.destination == str(signer().pubkey()):
        raise HTTPException(422, 'Withdrawal destination cannot be the treasury.')
    asset = await asset_by_id(body.asset_id)
    amount = to_units(body.amount, asset['decimals'])
    if amount > int(os.environ['MAX_WITHDRAWAL_BASE_UNITS']):
        raise HTTPException(422, 'Amount exceeds the configured devnet withdrawal limit.')
    vault = await db.vaults.find_one({'user_id': user['id']}, {'_id': 0, 'balances': 1})
    if (vault or {}).get('balances', {}).get(asset['id'], {}).get('available', 0) < amount:
        raise HTTPException(409, 'Insufficient available balance.')
    payment = {'id': uid(), 'user_id': user['id'], 'idempotency_key': body.idempotency_key,
        'asset_id': asset['id'], 'symbol': asset['symbol'], 'mint_address': asset['mint_address'],
        'amount': body.amount, 'amount_base_units': str(amount), 'destination': body.destination,
        'source': str(signer().pubkey()), 'status': 'PENDING', 'type': 'WITHDRAWAL',
        'network': 'devnet', 'created_at': now().isoformat(), 'updated_at': now().isoformat()}
    try:
        await db.payments.insert_one(payment.copy())
    except DuplicateKeyError:
        existing = await db.payments.find_one({'user_id': user['id'], 'idempotency_key': body.idempotency_key}, PUBLIC_PROJECTION)
        if any(existing[field] != value for field, value in [('asset_id', body.asset_id), ('amount', body.amount), ('destination', body.destination)]):
            raise HTTPException(409, 'Idempotency key already used with different payment details.')
        return existing
    background.add_task(process_payment, payment['id'])
    return payment


@router.get('/transactions', response_model=list[Document])
async def history(kind: str = Query('ALL', pattern='^(ALL|DEPOSIT|WITHDRAWAL|TIP)$'), user=Depends(current_user)):
    query = {'user_id': user['id']}
    deposits = await db.deposits.find(query, PUBLIC_PROJECTION).sort('created_at', -1).to_list(100) if kind in ['ALL', 'DEPOSIT'] else []
    payments = await db.payments.find({**query, **({'type': kind} if kind != 'ALL' else {})}, PUBLIC_PROJECTION).sort('created_at', -1).to_list(100) if kind != 'DEPOSIT' else []
    return sorted(deposits + payments, key=lambda row: row['created_at'], reverse=True)[:100]


@router.get('/tips', response_model=list[Document])
async def tips(user=Depends(current_user)):
    return await db.payments.find({'user_id': user['id'], 'type': 'TIP'}, PUBLIC_PROJECTION).sort('created_at', -1).to_list(100)


@router.get('/claims', response_model=list[Document])
async def claims(user=Depends(current_user)):
    if not user.get('x_user_id'):
        return []
    return await db.pending_claims.find({'recipient_x_user_id': user['x_user_id']}, {'_id': 0}).to_list(100)


@router.post('/claims/{claim_id}/claim')
async def claim(claim_id: str, user=Depends(current_user)):
    if not user.get('x_user_id'):
        raise HTTPException(403, 'Verified X identity is required to claim tips. X integration is not configured.')
    raise HTTPException(503, 'Claim payouts are not enabled until the X identity and bot integration phase is complete.')