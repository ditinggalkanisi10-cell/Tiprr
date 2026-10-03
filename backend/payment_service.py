"""Durable payment state machine. Signed bytes are stored BEFORE broadcasting.

Retries rebroadcast identical bytes only. No blind re-signing after timeouts.
"""
from fastapi import HTTPException
from core import db, now
from ledger import mutate
from chain import build_transaction, signer, rpc, finalized, verify_receipt

PUBLIC_PROJECTION = {'_id': 0, 'signed_transaction': 0, 'message': 0}


async def process_payment(payment_id):
    payment = await db.payments.find_one({'id': payment_id}, {'_id': 0})
    if not payment or payment['status'] in ['COMPLETED', 'FAILED', 'CANCELLED']:
        return
    amount = int(payment['amount_base_units'])
    asset = await db.tokens.find_one({'id': payment['asset_id']}, {'_id': 0})
    try:
        # Recovery-safe: mutate() recognizes the same reserve reference after a crash.
        await mutate(payment['user_id'], asset['id'], amount, 'reserve', payment['id'])
    except HTTPException:
        await db.payments.update_one({'id': payment_id, 'status': 'PENDING'}, {'$set': {
            'status': 'FAILED', 'error': 'Insufficient available balance.', 'updated_at': now().isoformat()}})
        return
    await db.payments.update_one({'id': payment_id, 'status': 'PENDING'}, {'$set': {'status': 'PROCESSING'}})
    if not payment.get('signature'):
        try:
            built = await build_transaction(asset, amount, str(signer().pubkey()), payment['destination'], payment_id, payout=True)
            # Competing workers may build, but only the atomic winner is ever submitted.
            await db.payments.update_one({'id': payment_id, 'signature': {'$exists': False}}, {'$set': {
                'signature': built['signature'], 'signed_transaction': built['transaction'],
                'last_valid_block_height': built['last_valid_block_height'], 'updated_at': now().isoformat()}})
        except HTTPException as error:
            await db.payments.update_one({'id': payment_id}, {'$set': {'error': str(error.detail), 'updated_at': now().isoformat()}})
            return
    payment = await db.payments.find_one({'id': payment_id}, {'_id': 0})
    if not payment.get('signature'):
        return
    try:
        tx = await finalized(payment['signature'])
        if tx and tx['meta']['err'] is not None:
            await mutate(payment['user_id'], asset['id'], amount, 'release', payment_id, payment['signature'])
            await db.payments.update_one({'id': payment_id}, {'$set': {'status': 'FAILED', 'error': 'Transaction failed on-chain. Reserved balance released.', 'updated_at': now().isoformat()}})
            return
        if tx:
            if not verify_receipt(tx, asset, amount, str(signer().pubkey()), payment['destination'], payment_id):
                await db.payments.update_one({'id': payment_id}, {'$set': {'error': 'Receipt requires manual reconciliation. Funds remain reserved.'}})
                return
            await mutate(payment['user_id'], asset['id'], amount, 'settle', payment_id, payment['signature'])
            await db.payments.update_one({'id': payment_id}, {'$set': {'status': 'COMPLETED', 'error': None, 'updated_at': now().isoformat()}})
            return
        height = await rpc('getBlockHeight', [{'commitment': 'finalized'}])
        if height > payment['last_valid_block_height']:
            await db.payments.update_one({'id': payment_id}, {'$set': {
                'error': 'Blockhash expired without a finalized receipt. Manual reconciliation required; funds remain reserved.'}})
            return
        await rpc('sendTransaction', [payment['signed_transaction'], {'encoding': 'base64', 'skipPreflight': False,
                                                                       'preflightCommitment': 'finalized', 'maxRetries': 0}])
    except HTTPException as error:
        await db.payments.update_one({'id': payment_id}, {'$set': {'error': str(error.detail), 'updated_at': now().isoformat()}})


async def reconcile_deposit(deposit):
    if deposit['status'] in ['COMPLETED', 'FAILED'] or not deposit.get('signature'):
        return
    asset = await db.tokens.find_one({'id': deposit['asset_id']}, {'_id': 0})
    tx = await finalized(deposit['signature'])
    if not tx:
        return
    if tx['meta']['err'] is not None:
        await db.deposits.update_one({'id': deposit['id']}, {'$set': {'status': 'FAILED', 'error': 'On-chain transaction failed. No balance was credited.'}})
        return
    if not verify_receipt(tx, asset, int(deposit['amount_base_units']), deposit['source'], deposit['destination'], deposit['id']):
        await db.deposits.update_one({'id': deposit['id']}, {'$set': {'status': 'FAILED', 'error': 'Receipt verification failed. No balance was credited.'}})
        return
    await mutate(deposit['user_id'], asset['id'], int(deposit['amount_base_units']), 'credit', deposit['id'], deposit['signature'])
    await db.deposits.update_one({'id': deposit['id']}, {'$set': {'status': 'COMPLETED', 'error': None, 'updated_at': now().isoformat()}})
