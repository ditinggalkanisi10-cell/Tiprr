import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Copy, Check, Loader2, ShieldCheck, Info, Wallet, RefreshCw } from 'lucide-react';
import { Transaction } from '@solana/web3.js';
import { Buffer } from 'buffer';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { PageHeading, ConnectPrompt, StatusBadge } from '../components/Shared';
import { useApp } from '../context/AppContext';
import { api, errorText, explorer } from '../lib/api';

window.Buffer = Buffer;

export default function Transfer({ mode = 'deposit' }) {
  const deposit = mode === 'deposit';
  const { user, provider, setProvider, setWalletOpen, status } = useApp();
  const [params] = useSearchParams();
  const [tokens, setTokens] = useState([]), [balances, setBalances] = useState([]);
  const [assetId, setAssetId] = useState('native-sol'), [amount, setAmount] = useState('');
  const [destination, setDestination] = useState(''), [mint, setMint] = useState('');
  const [custom, setCustom] = useState(params.get('custom') === 'true');
  const [busy, setBusy] = useState(false), [resolving, setResolving] = useState(false), [error, setError] = useState('');
  const [result, setResult] = useState(null), [copied, setCopied] = useState(false);
  const idempotency = useRef(crypto.randomUUID());
  const selected = tokens.find(t => t.id === assetId);
  const balance = balances.find(b => b.id === assetId)?.available || '0';
  useEffect(() => { api.get('/tokens').then(r => setTokens(r.data)).catch(e => setError(errorText(e))); }, []);
  useEffect(() => { if (user) { setDestination(user.wallet); api.get('/balances').then(r => setBalances(r.data)).catch(e => setError(errorText(e))); } else setBalances([]); }, [user]);
  const resolve = async () => {
    if (!user) { setWalletOpen(true); return; }
    setResolving(true); setError('');
    try { const { data } = await api.post('/tokens/resolve', { mint_address: mint.trim() }); setTokens(prev => [...prev.filter(t => t.id !== data.id), data]); setAssetId(data.id); setCustom(false); toast.success('Devnet mint verified on-chain'); }
    catch (e) { setError(errorText(e)); } finally { setResolving(false); }
  };
  const getProvider = async () => {
    const wallet = provider || window.phantom?.solana || window.solflare;
    if (!wallet) throw new Error('Open your wallet browser or install Phantom / Solflare.');
    const connected = await wallet.connect();
    if ((connected?.publicKey || wallet.publicKey).toString() !== user.wallet) throw new Error('Your active wallet does not match this session. Reconnect the correct wallet.');
    setProvider(wallet); return wallet;
  };
  const submit = async event => {
    event.preventDefault(); if (!user) { setWalletOpen(true); return; }
    setBusy(true); setError('');
    try {
      if (deposit) {
        const wallet = await getProvider();
        const { data } = await api.post('/deposit/create', { asset_id: assetId, amount });
        const tx = Transaction.from(Buffer.from(data.unsigned_transaction, 'base64'));
        const signed = await wallet.signTransaction(tx);
        const submitted = await api.post(`/deposits/${data.id}/submit`, { signed_transaction: Buffer.from(signed.serialize()).toString('base64') });
        setResult(submitted.data); toast.info(submitted.data.status === 'COMPLETED' ? 'Deposit finalized' : 'Submitted. Waiting for blockchain finality.');
      } else {
        const { data } = await api.post('/withdraw', { asset_id: assetId, amount, destination: destination.trim(), idempotency_key: idempotency.current });
        setResult(data); toast.info('Withdrawal queued. Your balance will be reserved.');
      }
    } catch (e) { setError(e.response ? errorText(e) : e.message || 'Request cancelled.'); } finally { setBusy(false); }
  };
  const refresh = async () => {
    setBusy(true);
    try { if (deposit) setResult((await api.get(`/deposits/${result.id}`)).data); else { const rows = (await api.get('/transactions')).data; setResult(rows.find(r => r.id === result.id) || result); } }
    catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const copy = async () => { try { await navigator.clipboard.writeText(status.signer.public_key); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { toast.error('Clipboard unavailable.'); } };
  return <><PageHeading eyebrow={deposit ? 'A LITTLE FUEL FOR GOOD ENERGY' : 'BACK TO YOUR WALLET'} title={deposit ? 'Add to your balance.' : 'Take your tokens with you.'} description={deposit ? 'SOL or your favorite supported Solana token.' : 'Your available assets, sent to the wallet you choose.'}/>{!user && <ConnectPrompt/>}<div className="transfer-layout"><section className="transfer-form-section"><div className="section-line"><h2 data-testid="transfer-title">{deposit ? 'Deposit' : 'Withdraw'}</h2><span className="testnet-tag" data-testid="transfer-network">SOLANA DEVNET</span></div><form onSubmit={submit} className="transfer-form">
    <label htmlFor="asset-select">Asset</label><select id="asset-select" className="form-select" value={custom ? 'custom' : assetId} data-testid="asset-select" onChange={e => { setError(''); setResult(null); idempotency.current = crypto.randomUUID(); if (e.target.value === 'custom') setCustom(true); else { setCustom(false); setAssetId(e.target.value); } }}><option value="native-sol">SOL — Solana</option>{tokens.filter(t => t.id !== 'native-sol').map(t => <option key={t.id} value={t.id}>{t.symbol} — {t.name}</option>)}{deposit && <option value="custom">+ Custom SPL token</option>}</select>
    {custom && <div className="custom-token-form"><label htmlFor="mint-address">Token mint address</label><Input id="mint-address" data-testid="mint-address-input" placeholder="Paste a Solana devnet mint address" value={mint} onChange={e => setMint(e.target.value)}/><Button type="button" variant="outline" data-testid="resolve-mint-button" disabled={resolving || !mint.trim()} onClick={resolve}>{resolving ? <Loader2 className="spin"/> : <ShieldCheck size={15}/>} Verify mint</Button><p data-testid="mint-note">Decimals and token program are read from Solana. Mainnet mints are not valid on devnet.</p></div>}
    {selected?.mint_address && !custom && <div className="mint-details" data-testid="selected-mint-details"><code>{selected.mint_address}</code><span>{selected.decimals} decimals · On-chain verified mint</span></div>}
    <div className="field-label"><label htmlFor="transfer-amount">Amount</label>{!deposit && <span data-testid="withdraw-available">Available: {balance} {selected?.symbol}</span>}</div><div className="amount-input-wrap"><Input id="transfer-amount" data-testid="transfer-amount" placeholder="0.00" inputMode="decimal" autoComplete="off" required value={amount} onChange={e => { setAmount(e.target.value); setResult(null); idempotency.current = crypto.randomUUID(); }}/><span>{selected?.symbol || 'SOL'}</span></div>
    {!deposit && <><label htmlFor="destination">Destination wallet</label><Input id="destination" data-testid="withdraw-destination" placeholder="Solana wallet address" required value={destination} onChange={e => { setDestination(e.target.value); setResult(null); idempotency.current = crypto.randomUUID(); }}/><p className="field-hint" data-testid="destination-note">Double-check the address. Confirmed transfers cannot be reversed.</p></>}
    <div className="transfer-info" data-testid="transfer-safety"><Info size={16}/><p>{deposit ? 'Deposits are credited only after blockchain finality. Your wallet may also need SOL for network fees and token account rent.' : 'Your available balance is reserved before a transfer. The treasury pays the network fee and any required token account rent.'}</p></div>
    {error && <div className="form-error" role="alert" data-testid="transfer-error">{error}</div>}
    <Button type={user ? 'submit' : 'button'} onClick={!user ? () => setWalletOpen(true) : undefined} className="primary-button transfer-submit" data-testid="transfer-submit" disabled={busy || custom || !!result}>{busy ? <Loader2 className="spin"/> : !user ? <Wallet size={17}/> : <ArrowUpRight size={17}/>} {!user ? 'Connect wallet to continue' : deposit ? 'Deposit from wallet' : 'Request withdrawal'}</Button>
    <p className="fine-print" data-testid="transfer-real-funds-warning">DEVNET ONLY. Never send real funds.</p>
    </form>{result && <div className="transfer-result" data-testid="transfer-result"><div><strong>{result.amount} {result.symbol}</strong><StatusBadge status={result.status} id="transfer-result-status"/></div><p data-testid="transfer-result-message">{result.status === 'COMPLETED' ? 'Verified on-chain and recorded in your ledger.' : 'Not yet finalized. Check the transaction status for the latest confirmation.'}</p>{result.error && <p className="form-error" data-testid="transfer-result-error">{result.error}</p>}<div className="result-actions"><Button variant="outline" disabled={busy} data-testid="refresh-transfer-status" onClick={refresh}><RefreshCw size={14}/> Refresh status</Button>{result.signature && <a href={explorer(result.signature)} target="_blank" rel="noreferrer" data-testid="transfer-explorer">Solana Explorer <ArrowUpRight size={13}/></a>}<Button variant="ghost" data-testid="new-transfer" onClick={() => { setResult(null); setAmount(''); idempotency.current = crypto.randomUUID(); }}>New {mode}</Button></div></div>}</section><aside className="transfer-aside"><span className="aside-symbol"><ShieldCheck size={28}/></span><h2 data-testid="transfer-aside-title">A clear trail. Every token.</h2><p data-testid="transfer-aside-description">The exact asset. Integer amounts. A permanent ledger entry for every confirmed movement.</p>{deposit && status?.signer?.public_key && <div className="treasury-info"><span className="small-label" data-testid="treasury-label">DEVNET TREASURY</span><code data-testid="treasury-address">{status.signer.public_key}</code><Button variant="outline" data-testid="copy-treasury" onClick={copy}>{copied ? <Check size={14}/> : <Copy size={14}/>} {copied ? 'Copied' : 'Copy address'}</Button><p className="warning-copy" data-testid="treasury-warning">Use the deposit button, not a direct transfer. Only signed deposits with your unique reference can be credited automatically. For tokens, only send the selected mint.</p></div>}<Link to="/activity" className="subtle-link" data-testid="transfer-history-link">View your activity <ArrowUpRight size={14}/></Link></aside></div></>;
}