import { Link } from 'react-router-dom';
import { ArrowUpRight, ArrowRight, ChevronRight, Wallet, MessageSquare, Heart, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '../components/ui/button';
import { Brand, BrandImage, XIcon, Network } from '../components/Brand';
import { BotDemo } from '../components/BotDemo';
import { useApp } from '../context/AppContext';

export default function Home() {
  const { setLoginOpen } = useApp();
  return <div className="home-page">
    <header className="site-header wrap"><Brand/><nav className="desktop-nav" aria-label="Main navigation"><a href="#how-it-works" data-testid="nav-how-it-works">How it works</a><a href="#assets" data-testid="nav-assets">Supported assets</a><Link to="/status" data-testid="nav-status">Status <span className="nav-status-dot"/></Link></nav><div className="header-actions"><Link to="/dashboard" className="header-dashboard" data-testid="nav-dashboard">Dashboard <ArrowUpRight size={14}/></Link><Button className="login-button" onClick={() => setLoginOpen(true)} data-testid="nav-login"><XIcon size={14}/> Login with X</Button></div></header>
    <main>
      <section className="hero" data-testid="home-hero">
        <div className="hero-grid" aria-hidden="true"/>
        <div className="hero-corner corner-left" aria-hidden="true">+</div><div className="hero-corner corner-right" aria-hidden="true">+</div>
        <motion.div className="hero-inner wrap" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .6 }}>
          <div className="hero-eyebrow" data-testid="hero-eyebrow"><span className="status-dot"/> LITTLE TIPS. BIG INTERNET ENERGY.</div>
          <div className="hero-title-group"><h1 data-testid="hero-heading">Tip anyone on <span className="hero-x">X<span className="x-spark">✳</span></span>.</h1><BrandImage className="hero-brand-art" testId="hero-logo"/><span className="hero-brand-caption" aria-hidden="true">your friendly<br/>neighborhood tip bot ↗</span></div>
          <p className="hero-description" data-testid="hero-description">A great take. A good meme. A little thank you.<br/>Send Solana tokens with a tweet. We’ll handle the rest.</p>
          <div className="hero-actions"><Button className="primary-button" data-testid="hero-login" onClick={() => setLoginOpen(true)}><XIcon/> Login with X <ArrowUpRight size={17}/></Button><Link to="/dashboard" data-testid="hero-explore" className="text-button">Explore TIPRR <ArrowRight size={15}/></Link></div>
          <div className="hero-meta" data-testid="hero-meta"><ShieldCheck size={12}/> Deposit once. Tip whenever. <span>Built on Solana <span className="solana-mini">≋</span></span></div>
          <div className="demo-stage"><span className="demo-annotation" aria-hidden="true">looks like a tweet.<br/>feels like a high five.<span>↘</span></span><BotDemo/><span className="demo-right-note" aria-hidden="true">LESS FRICTION.<br/>MORE APPRECIATION.<span>✦</span></span></div>
        </motion.div>
      </section>
      <section className="asset-band" id="assets"><div className="wrap asset-band-inner"><span className="small-label" data-testid="asset-band-title">SAME TIP. YOUR TOKEN.</span><div className="asset-list" data-testid="supported-assets"><span><i className="coin sol-coin">≋</i>SOL</span><span><i className="coin bonk-coin">฿</i>BONK</span><span><i className="coin usdc-coin">$</i>USDC</span><span><i className="coin wif-coin">w</i>WIF</span><span className="custom-asset">+ your SPL token</span></div><span className="asset-network-note" data-testid="asset-network-note">Use devnet mints only</span></div></section>
      <section id="how-it-works" className="how-section wrap"><div className="section-top"><div><span className="small-label" data-testid="how-eyebrow">NO EXTRA STEPS. NO BIG DEAL.</span><h2 className="section-heading" data-testid="how-heading">From “nice post” to “here’s a tip.”</h2></div><span className="handwritten" aria-hidden="true">as simple as it should be ↙</span></div><div className="steps-grid">{[{ Icon: XIcon, title: 'Make yourself known.', body: 'Your X account is your identity. No wallet addresses in the replies.', n: '01' }, { Icon: Wallet, title: 'Add a little something.', body: 'Connect your wallet. Deposit SOL or a supported Solana token.', n: '02' }, { Icon: MessageSquare, title: 'Tweet. Tip. Done.', body: 'Drop a /tiprr command. Your favorite people get the appreciation.', n: '03' }].map(({ Icon, title, body, n }) => <div className="step" key={n} data-testid={`how-step-${n}`}><div className="step-top"><Icon size={22}/><span>{n}</span></div><h3>{title}</h3><p>{body}</p></div>)}</div></section>
      <section className="bottom-cta wrap"><BrandImage testId="bottom-cta-logo"/><div><h2 data-testid="bottom-heading">Make someone’s timeline a little better.</h2><p data-testid="bottom-subtitle">Good internet energy starts with you.</p></div><Button className="primary-button" data-testid="bottom-login" onClick={() => setLoginOpen(true)}>Let’s tip <ArrowUpRight size={16}/></Button></section>
    </main>
    <footer className="site-footer wrap" data-testid="site-footer"><span data-testid="footer-message">Made for the good side of the internet. <Heart size={12}/></span><Link to="/status" data-testid="footer-network-link"><Network testId="footer-network"/><ChevronRight size={12}/></Link></footer>
    <div className="development-bar" data-testid="development-banner"><span className="tiny-square"/> DEVELOPMENT MODE — NO REAL FUNDS <span className="dev-bar-divider">/</span><Link to="/status" data-testid="development-status-link">X & bot setup pending <ArrowUpRight size={11}/></Link></div>
  </div>;
}
