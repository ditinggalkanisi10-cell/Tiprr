import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { api, errorText, setCsrfToken } from '../lib/api';

const Context = createContext(null);
export const useApp = () => useContext(Context);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(null);
  const [walletOpen, setWalletOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [provider, setProvider] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshUser = useCallback(async () => {
    try { const { data } = await api.get('/me'); setCsrfToken(data.csrf_token); setUser(data); }
    catch (e) { if (e.response?.status === 401) { setUser(null); setCsrfToken(null); } }
    finally { setLoading(false); }
  }, []);
  const refreshStatus = useCallback(async () => {
    try { setStatus((await api.get('/system/status')).data); }
    catch { setStatus({ api_error: true }); }
  }, []);
  useEffect(() => { refreshUser(); refreshStatus(); }, [refreshUser, refreshStatus]);
  const logout = async () => {
    try { await api.post('/auth/logout'); setUser(null); setProvider(null); setCsrfToken(null); toast.success('Wallet disconnected'); }
    catch (e) { toast.error(errorText(e)); }
  };
  return <Context.Provider value={{ user, status, loading, refreshUser, refreshStatus, walletOpen, setWalletOpen,
    loginOpen, setLoginOpen, provider, setProvider, logout }}>{children}</Context.Provider>;
}
