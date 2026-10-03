import { BrowserRouter, Routes, Route, useLocation, Link } from 'react-router-dom';
import { useEffect } from 'react';
import { Toaster } from 'sonner';
import { AppProvider } from './context/AppContext';
import { ConnectionDialogs } from './components/ConnectionDialogs';
import { AppLayout } from './components/AppLayout';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Transfer from './pages/Transfer';
import Activity from './pages/Activity';
import Claims from './pages/Claims';
import Profile from './pages/Profile';
import Status from './pages/Status';
import Admin from './pages/Admin';
import './App.css';

const ScrollReset = () => { const { pathname } = useLocation(); useEffect(() => { window.scrollTo(0, 0); }, [pathname]); return null; };
function App() {
  return <BrowserRouter><AppProvider><ScrollReset/><Routes><Route path="/" element={<Home/>}/><Route element={<AppLayout/>}><Route path="/dashboard" element={<Dashboard/>}/><Route path="/deposit" element={<Transfer key="deposit"/>}/><Route path="/withdraw" element={<Transfer key="withdraw" mode="withdraw"/>}/><Route path="/activity" element={<Activity/>}/><Route path="/claims" element={<Claims/>}/><Route path="/profile" element={<Profile/>}/><Route path="/status" element={<Status/>}/><Route path="/admin" element={<Admin/>}/><Route path="*" element={<div className="not-found"><h1 data-testid="not-found-heading">A little lost?</h1><Link to="/dashboard" data-testid="not-found-home">Back to your corner of TIPRR →</Link></div>}/></Route></Routes><ConnectionDialogs/><Toaster theme="dark" richColors position="bottom-right"/></AppProvider></BrowserRouter>;
}
export default App;
