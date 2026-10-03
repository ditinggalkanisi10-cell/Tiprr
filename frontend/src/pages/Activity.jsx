import { useEffect, useState } from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { PageHeading, EmptyState, ConnectPrompt, Transactions, Loading } from '../components/Shared';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { api, errorText } from '../lib/api';
import { useApp } from '../context/AppContext';

export default function Activity() {
  const { user } = useApp();
  const [rows, setRows] = useState([]), [filter, setFilter] = useState('ALL'), [search, setSearch] = useState(''), [loading, setLoading] = useState(false);
  const load = async () => { if (!user) return; setLoading(true); try { setRows((await api.get('/transactions')).data); } catch (e) { toast.error(errorText(e)); } finally { setLoading(false); } };
  useEffect(() => { if (!user) setRows([]); else { setLoading(true); api.get('/transactions').then(r => setRows(r.data)).catch(e => toast.error(errorText(e))).finally(() => setLoading(false)); } }, [user]);
  const filtered = rows.filter(r => (filter === 'ALL' || r.type === filter) && `${r.symbol} ${r.destination} ${r.signature || ''} ${r.mint_address || ''}`.toLowerCase().includes(search.toLowerCase()));
  return <><PageHeading eyebrow="EVERY LITTLE MOVEMENT" title="Your activity." description="Deposits, tips, and withdrawals. All in one place." action={<Button variant="outline" data-testid="refresh-activity" onClick={load} disabled={!user || loading}><RefreshCw size={15} className={loading ? 'spin' : ''}/>Refresh</Button>}/>{!user && <ConnectPrompt/>}<div className="activity-toolbar"><div className="filter-tabs">{[['ALL', 'All activity'], ['DEPOSIT', 'Deposits'], ['TIP', 'Tips'], ['WITHDRAWAL', 'Withdrawals']].map(([value, label]) => <button key={value} data-testid={`activity-filter-${value.toLowerCase()}`} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{label}</button>)}</div><div className="search-input"><Search size={16}/><Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search asset, mint, or address" data-testid="activity-search"/></div></div>{loading ? <Loading/> : filtered.length ? <Transactions rows={filtered} prefix="activity"/> : <EmptyState id="activity-empty" title={search ? 'No matching activity.' : 'A fresh start.'} description={search ? 'Try a different asset or wallet address.' : 'Your first deposit starts the story. Nothing has moved yet.'}/>}<div className="activity-count" data-testid="activity-count">{filtered.length} {filtered.length === 1 ? 'transaction' : 'transactions'} · Solana devnet</div></>;
}
