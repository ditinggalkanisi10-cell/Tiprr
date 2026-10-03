import { Link } from 'react-router-dom';

export const Bot = ({ className = '', testId = 'bot-mascot' }) => <img data-testid={testId} className={`pixel-bot ${className}`} src="/tiprr-bot.png" alt="TIPRR pixel robot" />;

export const Brand = ({ testId = 'brand-home' }) => <Link to="/" className="brand" data-testid={testId}><Bot testId={`${testId}-mascot`} /><span>TIPRR<span className="brand-period">.</span></span></Link>;

export const XIcon = ({ size = 18 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-6.78 7.75L23.2 22h-6.25l-4.9-7.43L5.55 22H2.4l7.15-8.18L1.8 2h6.4l4.43 6.76L18.9 2Zm-1.1 18h1.73L7.26 3.9H5.4L17.8 20Z"/></svg>;

export const Network = ({ testId = 'network-badge' }) => <span className="network-label" data-testid={testId}><span className="status-dot" /> Solana devnet</span>;
