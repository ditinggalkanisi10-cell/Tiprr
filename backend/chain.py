import base64
import os
import httpx
from fastapi import HTTPException
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.hash import Hash
from solders.message import Message
from solders.transaction import Transaction
from solders.instruction import Instruction
from solders.system_program import transfer, TransferParams
from spl.token.constants import TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID
from spl.token.instructions import (get_associated_token_address,
    create_idempotent_associated_token_account, transfer_checked, TransferCheckedParams)

MEMO = Pubkey.from_string('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr')


def signer():
    if os.environ.get('BOT_MODE') != 'development' or os.environ.get('SOLANA_NETWORK') != 'devnet':
        raise HTTPException(503, 'This isolated signer is restricted to development on Solana devnet.')
    secret = os.environ.get('OPERATIONAL_WALLET_SIGNER')
    if not secret:
        raise HTTPException(503, 'OPERATIONAL_WALLET_SIGNER is not configured.')
    return Keypair.from_base58_string(secret)


async def rpc(method, params=None):
    url = os.environ.get('SOLANA_RPC_URL')
    if not url:
        raise HTTPException(503, 'SOLANA_RPC_URL is not configured.')
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or []})
            response.raise_for_status()
            body = response.json()
        if body.get('error'):
            # Provider error bodies can contain URLs/credentials: never return them.
            raise HTTPException(502, 'Solana RPC rejected the request. No confirmation has been assumed.')
        return body['result']
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(503, 'Solana devnet RPC is currently unavailable. Please try again.')


async def assert_devnet():
    if os.environ.get('SOLANA_NETWORK') != 'devnet':
        raise HTTPException(503, 'Only Solana devnet is enabled in this build.')
    actual = await rpc('getGenesisHash')
    if actual != os.environ.get('SOLANA_EXPECTED_GENESIS_HASH'):
        raise HTTPException(503, 'RPC network mismatch. All money movement is blocked.')


async def resolve_mint(mint):
    try:
        Pubkey.from_string(mint)
    except ValueError:
        raise HTTPException(422, 'Invalid Solana mint address.')
    await assert_devnet()
    result = await rpc('getAccountInfo', [mint, {'encoding': 'jsonParsed', 'commitment': 'finalized'}])
    value = result.get('value')
    if not value or value.get('owner') not in [str(TOKEN_PROGRAM_ID), str(TOKEN_2022_PROGRAM_ID)]:
        raise HTTPException(422, 'This address is not a supported token mint on devnet.')
    data = value.get('data', {})
    if not isinstance(data, dict) or data.get('parsed', {}).get('type') != 'mint':
        raise HTTPException(422, 'The account is not an initialized mint.')
    info = data['parsed']['info']
    if not info.get('isInitialized') or not 0 <= info.get('decimals', -1) <= 18:
        raise HTTPException(422, 'This token is currently unsupported.')
    # Conservative Token-2022 policy: reject all extensions, including unknown ones.
    if info.get('extensions') or info.get('freezeAuthority'):
        raise HTTPException(422, 'Tokens with extensions or freeze authority are currently unsupported.')
    return {'asset_type': 'spl', 'mint_address': mint, 'decimals': info['decimals'],
            'token_program': value['owner'], 'symbol': mint[:4] + '…' + mint[-4:],
            'name': 'Custom SPL token', 'verified': False, 'network': 'devnet'}


async def build_transaction(asset, amount, owner, destination, reference, payout=False):
    await assert_devnet()
    sender, receiver = Pubkey.from_string(owner), Pubkey.from_string(destination)
    ixs = []
    if asset['asset_type'] == 'native':
        ixs.append(transfer(TransferParams(from_pubkey=sender, to_pubkey=receiver, lamports=amount)))
    else:
        fresh = await resolve_mint(asset['mint_address'])
        if fresh['decimals'] != asset['decimals'] or fresh['token_program'] != asset['token_program']:
            raise HTTPException(422, 'Mint configuration changed; transfer blocked.')
        mint, program = Pubkey.from_string(asset['mint_address']), Pubkey.from_string(asset['token_program'])
        source = get_associated_token_address(sender, mint, program)
        target = get_associated_token_address(receiver, mint, program)
        ixs.extend([create_idempotent_associated_token_account(sender, receiver, mint, program),
            transfer_checked(TransferCheckedParams(program_id=program, source=source, mint=mint,
                dest=target, owner=sender, amount=amount, decimals=asset['decimals']))])
    ixs.append(Instruction(MEMO, reference.encode(), []))
    latest = (await rpc('getLatestBlockhash', [{'commitment': 'finalized'}]))['value']
    blockhash = Hash.from_string(latest['blockhash'])
    tx = Transaction.new_unsigned(Message.new_with_blockhash(ixs, sender, blockhash))
    if payout:
        tx.sign([signer()], blockhash)
    return {'transaction': base64.b64encode(bytes(tx)).decode(),
            'message': base64.b64encode(bytes(tx.message)).decode(),
            'last_valid_block_height': latest['lastValidBlockHeight'],
            'signature': str(tx.signatures[0]) if payout else None}


def verify_signed(raw_b64, expected_message, wallet):
    try:
        raw = base64.b64decode(raw_b64, validate=True)
        if len(raw) > 1232:
            raise ValueError()
        tx = Transaction.from_bytes(raw)
        if base64.b64encode(bytes(tx.message)).decode() != expected_message:
            raise ValueError()
        if str(tx.message.account_keys[0]) != wallet:
            raise ValueError()
        tx.verify()
        return str(tx.signatures[0])
    except Exception:
        raise HTTPException(422, 'Signed transaction does not match the approved deposit.')


async def finalized(signature):
    return await rpc('getTransaction', [signature, {'encoding': 'jsonParsed', 'commitment': 'finalized',
                                                  'maxSupportedTransactionVersion': 0}])


def verify_receipt(tx, asset, amount, owner, destination, reference):
    if not tx or tx['meta']['err'] is not None:
        return False
    message = tx['transaction']['message']
    keys = [k['pubkey'] if isinstance(k, dict) else k for k in message['accountKeys']]
    if not keys or keys[0] != owner:
        return False
    instructions = message['instructions']
    memo_found = any(ix.get('program') == 'spl-memo' and ix.get('parsed') == reference for ix in instructions)
    if not memo_found:
        return False
    if asset['asset_type'] == 'native':
        matches = [ix for ix in instructions if ix.get('program') == 'system'
                   and ix.get('parsed', {}).get('type') == 'transfer'
                   and ix['parsed']['info'].get('source') == owner
                   and ix['parsed']['info'].get('destination') == destination
                   and ix['parsed']['info'].get('lamports') == amount]
        if not matches or destination not in keys:
            return False
        index = keys.index(destination)
        return tx['meta']['postBalances'][index] - tx['meta']['preBalances'][index] == amount
    mint, program = asset['mint_address'], asset['token_program']
    target = str(get_associated_token_address(Pubkey.from_string(destination), Pubkey.from_string(mint), Pubkey.from_string(program)))
    matches = [ix for ix in instructions if ix.get('programId') == program
               and ix.get('parsed', {}).get('type') == 'transferChecked'
               and ix['parsed']['info'].get('authority') == owner
               and ix['parsed']['info'].get('destination') == target
               and ix['parsed']['info'].get('mint') == mint
               and int(ix['parsed']['info'].get('tokenAmount', {}).get('amount', -1)) == amount]
    if not matches or target not in keys:
        return False
    index = keys.index(target)
    def token_balance(items):
        for item in items:
            if item['accountIndex'] == index and item['mint'] == mint and item.get('owner') == destination:
                return int(item['uiTokenAmount']['amount'])
        return 0
    return token_balance(tx['meta'].get('postTokenBalances', [])) - token_balance(tx['meta'].get('preTokenBalances', [])) == amount