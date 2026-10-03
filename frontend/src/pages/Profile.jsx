import { ArrowUpRight, Check, Wallet, Link2, LogOut } from 'lucide-react';
import { Button } from '../components/ui/button';
import { PageHeading } from '../components/Shared';
import { XIcon } from '../components/Brand';
import { useApp } from '../context/AppContext';
import { short } from '../lib/api';

export default function Profile() {
  const { user, setWalletOpen, setLoginOpen, logout } = useApp();
  return <><PageHeading eyebrow="THE DOTS, CONNECTED" title="Your connections." description="An identity for your tips. A wallet for your tokens."/><div className="profile-connections"><section className="connection-row"><div className="connection-logo"><XIcon size={25}/></div><div><h2 data-testid="profile-x-title">X account</h2><p data-testid="profile-x-status">{user?.username ? `@${user.username}` : 'Not connected'}</p><span className="fine-print" data-testid="profile-x-note">X login and bot access require configuration.</span></div><Button variant="outline" onClick={() => setLoginOpen(true)} data-testid="profile-connect-x">Connect X <ArrowUpRight size={14}/></Button></section><section className="connection-row"><div className="connection-logo"><Wallet size={25}/></div><div><h2 data-testid="profile-wallet-title">Solana wallet</h2><p data-testid="profile-wallet-address">{user ? short(user.wallet) : 'Not connected'}</p>{user && <span className="verified-note" data-testid="profile-wallet-verified"><Check size={12}/> Ownership verified</span>}</div>{user ? <Button variant="outline" data-testid="profile-disconnect" onClick={logout}><LogOut size={14}/>Disconnect</Button> : <Button variant="outline" data-testid="profile-connect-wallet" onClick={() => setWalletOpen(true)}>Connect wallet <ArrowUpRight size={14}/></Button>}</section></div><div className="profile-note"><Link2 size={20}/><p data-testid="profile-identity-note">TIPRR will use your permanent X user ID, not your username. A new handle won’t change who owns your tips.</p></div>{user && <div className="account-details" data-testid="account-details"><span>DEVNET ACCOUNT</span><code>{user.id}</code><p>Joined {new Date(user.created_at).toLocaleDateString()}</p></div>}</>;
}
