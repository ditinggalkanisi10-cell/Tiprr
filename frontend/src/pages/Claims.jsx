import { useEffect, useState } from 'react';
import { ShieldCheck, ArrowUpRight, Gift } from 'lucide-react';
import { Button } from '../components/ui/button';
import { EmptyState, PageHeading, StatusBadge } from '../components/Shared';
import { XIcon } from '../components/Brand';
import { useApp } from '../context/AppContext';
import { api, errorText } from '../lib/api';
import { toast } from 'sonner';

export default function Claims() {
  const { user, setLoginOpen } = useApp();
  const [claims, setClaims] = useState([]);
  useEffect(() => { if (user) api.get('/claims').then(r => setClaims(r.data)).catch(e => toast.error(errorText(e))); else setClaims([]); }, [user]);
  return <><PageHeading eyebrow="SOMEONE’S THINKING OF YOU" title="A little something for you." description="Tips waiting to make their way to your wallet."/><div className="claim-summary"><Gift size={25}/><div><span data-testid="claim-total-label">Pending claims</span><strong data-testid="claim-total">{claims.length}</strong></div><Button className="primary-button" disabled={!user?.x_connected || !claims.length} data-testid="claim-all-button">Claim all <ArrowUpRight size={16}/></Button></div>{!user?.x_connected && <div className="claim-identity"><div><ShieldCheck size={21}/><span><strong data-testid="claim-identity-heading">Your X identity is the key.</strong><p data-testid="claim-identity-description">Only the verified X account that received a tip can claim it. X authentication is not configured yet.</p></span></div><Button variant="outline" onClick={() => setLoginOpen(true)} data-testid="claims-connect-x"><XIcon size={14}/> Connect X</Button></div>}{claims.length ? claims.map(c => <div key={c.id} className="claim-row" data-testid={`claim-${c.id}`}><strong>{c.amount} {c.symbol}</strong><StatusBadge id={`claim-status-${c.id}`} status={c.status}/></div>) : <EmptyState id="claims-empty" title="Nothing waiting. Yet." description="When someone sends you a tip, this is where the good stuff lands."/>}</>;
}
