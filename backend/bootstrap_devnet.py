"""One-time local development configuration; never prints or commits private material."""
import os
import secrets
from pathlib import Path
from dotenv import dotenv_values
from solders.keypair import Keypair


def main():
    path = Path(__file__).parent / '.env'
    current = dotenv_values(path)
    frontend = dotenv_values(path.parent.parent / 'frontend' / '.env')
    values = {
        'APP_ORIGIN': frontend['REACT_APP_BACKEND_URL'],
        'BOT_MODE': 'development', 'SOLANA_NETWORK': 'devnet',
        'SOLANA_RPC_URL': 'https://api.devnet.solana.com',
        'SOLANA_EXPECTED_GENESIS_HASH': 'EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG',
        'OPERATIONAL_WALLET_SIGNER': str(Keypair()),
        'WEBHOOK_CRON_SECRET': secrets.token_urlsafe(48),
        'MAX_WITHDRAWAL_BASE_UNITS': '1000000000000',
        'ADMIN_WALLETS': '', 'X_ENABLED': 'false',
        'X_CLIENT_ID': '', 'X_CLIENT_SECRET': '', 'X_REDIRECT_URI': '',
        'X_BOT_ACCESS_TOKEN': '', 'USEPAID_API_KEY': '', 'USEPAID_API_URL': '',
    }
    with path.open('a') as file:
        for key, value in values.items():
            if key not in current:
                file.write(f'\n{key}="{value}"')
    os.chmod(path, 0o600)
    print('Isolated devnet configuration ready. Secrets were not printed.')


if __name__ == '__main__':
    main()
