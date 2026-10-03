"""Single-document atomic ledger for the initial standalone MongoDB build.

Journal entries are append-only. Available/reserved projections change in the SAME
Mongo write as the corresponding journal entry. No cross-document balance writes.
Bounded at 10,000 events per account; production needs PostgreSQL migration.
"""
from fastapi import HTTPException
from core import db, now
from amounts import MAX_UNITS


async def mutate(user_id, asset_id, amount, action, reference, signature=None):
    event_id = f'{action}:{reference}'
    path = f'balances.{asset_id}'
    query = {'user_id': user_id, 'journal.id': {'$ne': event_id}}
    # Reserve room for EVERY outstanding reservation to settle/release even
    # after the account reaches its incoming journal limit.
    if action in ['credit', 'reserve']:
        query['journal.9999'] = {'$exists': False}
    increments = {}
    if action == 'credit':
        query['$expr'] = {'$lte': [{'$add': [
            {'$ifNull': [f'${path}.available', 0]}, {'$ifNull': [f'${path}.reserved', 0]}, amount]}, MAX_UNITS]}
        increments[f'{path}.available'] = amount
    elif action == 'reserve':
        query[f'{path}.available'] = {'$gte': amount}
        increments = {f'{path}.available': -amount, f'{path}.reserved': amount}
    elif action in ['settle', 'release']:
        query[f'{path}.reserved'] = {'$gte': amount}
        query['$and'] = [{'journal.id': f'reserve:{reference}'},
                         {'journal.id': {'$ne': f'{"release" if action == "settle" else "settle"}:{reference}'}}]
        increments[f'{path}.reserved'] = -amount
        if action == 'release':
            increments[f'{path}.available'] = amount
    else:
        raise ValueError('Unknown ledger operation')
    event = {'id': event_id, 'asset_id': asset_id, 'amount_base_units': str(amount),
             'action': action, 'reference_id': reference, 'blockchain_signature': signature,
             'created_at': now().isoformat()}
    result = await db.vaults.update_one(query, {'$inc': increments, '$push': {'journal': event}})
    if result.modified_count:
        return True
    if await db.vaults.find_one({'user_id': user_id, 'journal.id': event_id}, {'_id': 0, 'user_id': 1}):
        return False
    raise HTTPException(409, 'Insufficient available balance or account ledger limit reached.')
