import { useEffect, useState } from 'react';
import { LockKeyhole, ShieldCheck } from 'lucide-react';
import { Button } from '../components/ui/button';
import { PageHeading, Transactions } from '../components/Shared';
import { useApp } from '../context/AppContext';
import { api, errorText } from '../lib/api';

export default function Admin() {
  const { user, setWalletOpen } = useApp();
  const [stats, setStats] = useState(null), [error, setError] = useState('');
  useEffect(() => { setStats(null); if (user) api.get('/admin/stats').then(r => { setStats(r.data); setError(''); }).catch(e => setError(errorText(e))); }, [user]);
  return <><PageHeading eyebrow="OPERATIONS" title="Under the hood." description="Protected access. No private keys, ever."/>{!stats ? <div className="admin-gate"><LockKeyhole size={36}/><h2 data-testid="admin-gate-title">Administrator access only.</h2><p data-testid="admin-gate-description">Sign with a wallet included in the server’s ADMIN_WALLETS allowlist.</p>{error && <div className="form-error" data-testid="admin-error">{error}</div>}<Button className="primary-button" onClick={() => setWalletOpen(true)} data-testid="admin-verify-wallet"><ShieldCheck size={16}/>Verify administrator wallet</Button></div> : <><div className="admin-stats">{Object.entries(stats).filter(([, value]) => typeof value === 'number').map(([key, value]) => <div key={key}><span data-testid={`admin-label-${key}`}>{key.replaceAll('_', ' ')}</span><strong data-testid={`admin-stat-${key}`}>{value}</strong></div>)}</div><div className="section-line"><h2 data-testid="admin-payments-title">Recent payments</h2></div><Transactions rows={stats.recent_payments} prefix="admin-payment"/></>}</>;
}
