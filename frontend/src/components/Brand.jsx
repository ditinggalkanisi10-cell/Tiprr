import { Link } from 'react-router-dom';

export const BrandImage = ({ className = '', testId = 'tiprr-logo' }) => <img data-testid={testId} className={`brand-art ${className}`} src="/tiprr-logo-smooth.png" alt="Tiprr pixel wordmark" />;

export const Brand = ({ testId = 'brand-home', className = '' }) => <Link to="/" className={`brand ${className}`} aria-label="TIPRR home" data-testid={testId}><BrandImage testId={`${testId}-logo`} /></Link>;

export const XIcon = ({ size = 18 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-6.78 7.75L23.2 22h-6.25l-4.9-7.43L5.55 22H2.4l7.15-8.18L1.8 2h6.4l4.43 6.76L18.9 2Zm-1.1 18h1.73L7.26 3.9H5.4L17.8 20Z"/></svg>;

export const Network = ({ testId = 'network-badge' }) => <span className="network-label" data-testid={testId}><span className="status-dot" /> Solana devnet</span>;
