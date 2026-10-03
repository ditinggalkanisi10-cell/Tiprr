import re
from decimal import Decimal
from fastapi import HTTPException

MAX_UNITS = 2**63 - 1


def to_units(amount: str, decimals: int) -> int:
    if not re.fullmatch(r'(?:0|[1-9]\d{0,18})(?:\.\d{1,18})?', amount):
        raise HTTPException(422, 'Amount must be a positive decimal number.')
    if '.' in amount and len(amount.split('.')[1]) > decimals:
        raise HTTPException(422, f'This asset supports at most {decimals} decimal places.')
    # String arithmetic avoids Decimal context rounding for large SPL values.
    parts = amount.split('.')
    value = int(parts[0]) * 10**decimals + int((parts[1] if len(parts) > 1 else '').ljust(decimals, '0') or '0')
    if not 0 < value <= MAX_UNITS:
        raise HTTPException(422, 'Amount is zero or exceeds the supported base-unit limit.')
    return value


def display_units(amount: int, decimals: int) -> str:
    sign = '-' if amount < 0 else ''
    raw = str(abs(amount)).zfill(decimals + 1)
    return sign + (raw if decimals == 0 else (raw[:-decimals] + '.' + raw[-decimals:]).rstrip('0').rstrip('.'))


def parse_command(text: str):
    match = re.fullmatch(r'\s*/tiprr\s+([0-9]+(?:\.[0-9]+)?)\s+([A-Za-z0-9]{1,44})\s+@([A-Za-z0-9_]{1,15})\s*', text)
    if not match or Decimal(match[1]) <= 0:
        raise HTTPException(422, 'Invalid format. Try: /tiprr 10 BONK @username')
    return {'amount': match[1], 'asset': match[2], 'recipient_username': match[3]}
