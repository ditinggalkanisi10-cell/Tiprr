"""Configuration and shared persistence. All funds in this build are devnet only."""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict

load_dotenv(Path(__file__).parent / '.env')
client = AsyncIOMotorClient(os.environ['MONGO_URL'], tz_aware=True)
db = client[os.environ['DB_NAME']]


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


class Document(BaseModel):
    model_config = ConfigDict(extra='allow')


async def initialize():
    for collection, field in [('users', 'id'), ('users', 'wallet'), ('vaults', 'user_id'),
                              ('tokens', 'id'), ('deposits', 'id'), ('payments', 'id'),
                              ('sessions', 'token_hash'), ('challenges', 'id'),
                              ('jobs', 'run_id'), ('x_posts', 'x_post_id')]:
        await db[collection].create_index(field, unique=True)
    await db.users.create_index('x_user_id', unique=True,
                               partialFilterExpression={'x_user_id': {'$type': 'string'}})
    for collection in ['sessions', 'challenges', 'rate_limits']:
        await db[collection].create_index('expires_at', expireAfterSeconds=0)
    await db.deposits.create_index('signature', unique=True,
                                  partialFilterExpression={'signature': {'$type': 'string'}})
    await db.payments.create_index([('user_id', 1), ('idempotency_key', 1)], unique=True)
    await db.tokens.create_index('mint_address', unique=True,
                                partialFilterExpression={'mint_address': {'$type': 'string'}})
    await db.tokens.update_one({'id': 'native-sol'}, {'$setOnInsert': {
        'id': 'native-sol', 'asset_type': 'native', 'mint_address': None,
        'symbol': 'SOL', 'name': 'Solana', 'decimals': 9, 'token_program': None,
        'verified': True, 'network': 'devnet', 'created_at': now().isoformat(),
    }}, upsert=True)
