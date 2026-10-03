import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ShieldCheck, Wallet, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { useApp } from '../context/AppContext';
import { api, errorText } from '../lib/api';
import { XIcon } from './Brand';

export const ConnectionDialogs = () => {
  const { walletOpen, setWalletOpen, loginOpen, setLoginOpen, setProvider, refreshUser } = useApp();
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const connect = async name => {
    setError('');
    const wallet = name === 'Phantom' ? window.phantom?.solana : window.solflare;
    if (!wallet) { setError(`${name} was not detected. Install the browser wallet, then return here. On mobile, open TIPRR in your wallet’s browser.`); return; }
    setBusy(name);
    try {
      const connected = await wallet.connect();
      const key = (connected?.publicKey || wallet.publicKey).toString();
      const { data } = await api.post('/wallet/challenge', { wallet: key });
      const signed = await wallet.signMessage(new TextEncoder().encode(data.message), 'utf8');
      const signature = btoa(String.fromCharCode(...(signed.signature || signed)));
      await api.post('/wallet/verify', { challenge_id: data.id, signature });
      setProvider(wallet); await refreshUser(); setWalletOpen(false); toast.success('Wallet ownership verified');
    } catch (e) { setError(e.code === 4001 ? 'Connection cancelled. Your wallet has not been changed.' : errorText(e)); }
    finally { setBusy(''); }
  };
  return <>
    <Dialog open={walletOpen} onOpenChange={open => { setWalletOpen(open); setError(''); }}>
      <DialogContent className="tiprr-dialog" data-testid="wallet-dialog">
        <div className="dialog-symbol"><Wallet size={25} /></div>
        <DialogHeader><DialogTitle data-testid="wallet-dialog-title">Connect your wallet</DialogTitle><DialogDescription data-testid="wallet-dialog-description">An ownership signature. No transaction. No fees.</DialogDescription></DialogHeader>
        <div className="devnet-notice" data-testid="wallet-devnet-notice">DEVNET ONLY — NO REAL FUNDS</div>
        {['Phantom', 'Solflare'].map((name, index) => <Button key={name} variant="outline" className="wallet-option" data-testid={`connect-${name.toLowerCase()}`} disabled={!!busy} onClick={() => connect(name)}><span className={`wallet-logo wallet-${index}`}>{index ? '✳' : '◕'}</span><span>{name}</span>{busy === name ? <Loader2 className="spin" /> : <ArrowUpRight />}</Button>)}
        {error && <div role="alert" className="form-error" data-testid="wallet-connect-error">{error}<div className="wallet-install-links"><a href="https://phantom.com/download" target="_blank" rel="noreferrer" data-testid="install-phantom">Get Phantom ↗</a><a href="https://solflare.com" target="_blank" rel="noreferrer" data-testid="install-solflare">Get Solflare ↗</a></div></div>}
        <p className="fine-print" data-testid="wallet-security-note"><ShieldCheck size={14} /> Your private keys never leave your wallet.</p>
      </DialogContent>
    </Dialog>
    <Dialog open={loginOpen} onOpenChange={setLoginOpen}>
      <DialogContent className="tiprr-dialog" data-testid="x-login-dialog">
        <div className="dialog-symbol"><XIcon size={26} /></div>
        <DialogHeader><DialogTitle data-testid="x-login-title">X is next on the list.</DialogTitle><DialogDescription data-testid="x-login-description">X login and automatic tipping are not connected yet. No X account or permission has been requested.</DialogDescription></DialogHeader>
        <div className="config-needed" data-testid="x-required-config"><span>CONFIGURATION REQUIRED</span><code>X_CLIENT_ID</code><code>X_CLIENT_SECRET</code><code>X_REDIRECT_URI</code><code>X_BOT_ACCESS_TOKEN</code></div>
        <Button className="primary-button" data-testid="x-dialog-wallet-button" onClick={() => { setLoginOpen(false); setWalletOpen(true); }}>Connect a devnet wallet <ArrowUpRight size={16}/></Button>
        <Link to="/status" className="subtle-link" data-testid="x-dialog-status-link" onClick={() => setLoginOpen(false)}>View integration status</Link>
      </DialogContent>
    </Dialog>
  </>;
};
