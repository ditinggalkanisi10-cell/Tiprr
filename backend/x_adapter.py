"""Official-API-only building blocks for the next integration phase.

Not attached to the live application until X OAuth, entitlement and bot
authorization are provided. No browser scraping and no synthetic events.
"""
import os
import httpx
from fastapi import HTTPException
from core import db


class XAdapter:
    def __init__(self):
        self.token = os.environ.get('X_BOT_ACCESS_TOKEN')
        self.base = os.environ.get('X_API_BASE_URL')
        if os.environ.get('X_ENABLED') != 'true' or not self.token or not self.base:
            raise HTTPException(503, 'Official X bot access is not configured.')

    async def request(self, method, path, **kwargs):
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, f'{self.base}{path}',
                headers={'Authorization': f'Bearer {self.token}'}, **kwargs)
        if response.status_code >= 400:
            raise HTTPException(502, 'X API request failed. Check access level, permissions and rate limits.')
        return response.json()

    async def resolve_user(self, username):
        return (await self.request('GET', f'/users/by/username/{username}',
            params={'user.fields': 'profile_image_url,name,username'}))['data']

    async def recent_posts(self, since_id=None, next_token=None):
        params = {'query': '"/tiprr" -is:retweet', 'tweet.fields': 'author_id,created_at', 'max_results': 100}
        if since_id:
            params['since_id'] = since_id
        if next_token:
            params['next_token'] = next_token
        return await self.request('GET', '/tweets/search/recent', params=params)

    async def reply(self, original_post_id, text):
        return await self.request('POST', '/tweets', json={'text': text,
            'reply': {'in_reply_to_tweet_id': original_post_id}})


async def resolve_asset(identifier):
    by_mint = await db.tokens.find_one({'mint_address': identifier}, {'_id': 0})
    if by_mint:
        return by_mint
    matches = await db.tokens.find({'symbol': identifier.upper()}, {'_id': 0}).to_list(500)
    verified = [token for token in matches if token.get('verified')]
    if len(verified) == 1:
        return verified[0]
    if len(matches) == 1:
        return matches[0]
    raise HTTPException(422, 'Unknown or ambiguous asset. Use its exact Solana mint address.')
