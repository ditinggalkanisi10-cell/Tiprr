import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownLeft, ArrowUpRight, ArrowRight, Copy, Check, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { PageHeading, EmptyState, ConnectPrompt, AssetIcon, Transactions } from '../components/Shared';
import { XIcon } from '../components/Brand';
import { useApp } from '../context/AppContext';
import { api, errorText, short } from '../lib/api';

export default function Dashboard() {
  const { user, setLoginOpen } = useApp();
  const [balances, setBalances] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!user) { setBalances([]); setTransactions([]); return; }
    Promise.all([api.get('/balances'), api.get('/transactions')]).then(([b, t]) => { setBalances(b.data); setTransactions(t.data); }).catch(e => toast.error(errorText(e)));
  }, [user]);
  const copy = async () => { try { await navigator.clipboard.writeText('/tiprr 0.02 SOL @tiprrx'); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { toast.error('Could not access clipboard.'); } };
  return <>
    <PageHeading eyebrow="YOUR TIPRR" title={user ? 'Good to have you here.' : 'A little good goes a long way.'} description={user ? short(user.wallet) : 'Your balance. Your tokens. Someone’s better day.'} action={<div className="page-action-pair"><Button asChild variant="outline" data-testid="dashboard-withdraw"><Link to="/withdraw"><ArrowUpRight size={16}/> Withdraw</Link></Button><Button asChild className="primary-button compact" data-testid="dashboard-deposit"><Link to="/deposit"><Plus size={16}/> Deposit</Link></Button></div>}/>
    {!user && <ConnectPrompt/>}
    <section className="balance-section"><div className="section-line"><h2 data-testid="balance-title">Your balance</h2><span className="small-label" data-testid="balance-network">DEVNET ASSETS</span></div><div className="balance-grid">{(balances.length ? balances : [{ id: 'native-sol', symbol: 'SOL', name: 'Solana', available: '0', reserved: '0' }]).map(asset => <div className="balance-asset" data-testid={`balance-${asset.id}`} key={asset.id}><div className="balance-asset-label"><AssetIcon symbol={asset.symbol}/><div><strong>{asset.symbol}</strong><span>{asset.name}</span></div><ArrowUpRight size={16}/></div><strong className="asset-amount" data-testid={`amount-${asset.id}`}>{user ? asset.available : '—'} <small>{asset.symbol}</small></strong><span className="balance-available" data-testid={`reserved-${asset.id}`}>{user ? `${asset.reserved} reserved` : 'Connect a wallet to see your balance'}</span></div>)}<Link to="/deposit?custom=true" className="add-token" data-testid="dashboard-add-token"><Plus size={24}/><strong>Your token belongs here.</strong><span>Add a custom SPL token <ArrowRight size={13}/></span></Link></div></section>
    <div className="dashboard-columns"><section><div className="section-line"><h2 data-testid="recent-activity-title">Recent activity</h2><Link to="/activity" className="subtle-link" data-testid="view-all-activity">View all <ArrowUpRight size={13}/></Link></div>{transactions.length ? <Transactions rows={transactions.slice(0, 5)} prefix="recent"/> : <EmptyState id="dashboard-activity-empty" title="Good things start somewhere." description="Your deposits, tips, and withdrawals will show up here." action={<Link to="/deposit" className="subtle-link" data-testid="first-deposit">Make your first deposit <ArrowRight size={14}/></Link>}/>}</section><section className="dashboard-side"><div className="section-line"><h2 data-testid="ready-to-tip-title">Your next little thank you</h2><XIcon size={15}/></div><div className="command-preview"><span className="small-label" data-testid="command-example-label">COMMAND EXAMPLE</span><code data-testid="dashboard-command">/tiprr 0.02 SOL @tiprrx</code><button className="icon-button" title="Copy command" data-testid="copy-tip-command" onClick={copy}>{copied ? <Check size={16}/> : <Copy size={16}/>}</button></div><div className="connection-status"><span data-testid="dashboard-x-state"><XIcon size={14}/> X account <i>Not connected</i></span><Button variant="outline" data-testid="dashboard-connect-x" onClick={() => setLoginOpen(true)}>Connect X <ArrowUpRight size={14}/></Button></div><Link to="/claims" className="claims-teaser" data-testid="dashboard-claims"><span>Something waiting for you?<small>Check your pending claims</small></span><ArrowUpRight size={18}/></Link></section></div>
  </>;
}
