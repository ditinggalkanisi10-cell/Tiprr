import { useEffect, useState } from 'react';
import { Check, Heart, MessageCircle, Repeat2, BarChart2, RotateCcw, Pause, Play } from 'lucide-react';
import { Bot, XIcon } from './Brand';

const examples = [
  { command: '/tiprr 0.02 SOL @tiprrx', amount: '0.02 SOL', who: '@tiprrx' },
  { command: '/tiprr 10 BONK @ryansshh', amount: '10 BONK', who: '@ryansshh' },
  { command: '/tiprr 5 USDC @alex', amount: '5 USDC', who: '@alex' },
];

export const BotDemo = () => {
  const [tick, setTick] = useState(0);
  const [paused, setPaused] = useState(false);
  const [example, setExample] = useState(0);
  const current = examples[example];
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  useEffect(() => {
    if (paused || reduced) return;
    const timer = setInterval(() => setTick(value => (value + 1) % 145), 70);
    return () => clearInterval(timer);
  }, [paused, reduced]);
  const typed = reduced ? current.command : current.command.slice(0, Math.max(0, tick - 8));
  const sent = reduced || tick > 57;
  const processing = tick > 42 && !sent;
  return <div className="bot-demo" data-testid="bot-demo">
    <div className="demo-topline"><span data-testid="demo-label"><span className="tiny-square"/> THE BOT, IN ACTION <span className="example-label">ILLUSTRATIVE EXAMPLE</span></span><div><button title={paused ? 'Play example' : 'Pause example'} aria-label={paused ? 'Play example' : 'Pause example'} onClick={() => setPaused(!paused)} data-testid="demo-pause">{paused ? <Play size={13}/> : <Pause size={13}/>}</button><button title="Replay example" aria-label="Replay example" onClick={() => { setTick(0); setPaused(false); }} data-testid="demo-replay"><RotateCcw size={13}/></button><XIcon size={15}/></div></div>
    <div className="tweet original-tweet"><div className="tweet-avatar human-avatar">a<span>✦</span></div><div className="tweet-content"><div className="tweet-author" data-testid="demo-author">alex <span>@alex · now</span><span className="tweet-ellipsis">···</span></div><p className="tweet-intro" data-testid="demo-post-intro">good posts deserve a little something.</p><p className="tweet-command" data-testid="demo-command">{typed}<span className={!sent && !paused ? 'typing-cursor' : 'typing-cursor invisible'} /></p><div className="tweet-actions" aria-hidden="true"><MessageCircle/><Repeat2/><Heart/><BarChart2/></div></div></div>
    <div className={`tweet reply-tweet ${sent ? 'reply-visible' : ''}`} data-testid="demo-reply" aria-hidden={!sent}><div className="tweet-avatar bot-avatar"><Bot testId="demo-reply-bot"/></div><div className="tweet-content"><div className="tweet-author" data-testid="demo-bot-name">TIPRR <span className="verified-check"><Check size={10}/></span><span>@tiprrx · now</span></div><p className="reply-text" data-testid="demo-reply-text">💸 Sent <strong>{current.amount}</strong> to <span>{current.who}</span></p><span className="reply-confirmed" data-testid="demo-example-confirmation"><Check size={11}/> Example response · no funds moved</span></div></div>
    {!sent && <div className="demo-processing" data-testid="demo-processing">{processing ? <><span className="processing-dots">•••</span> TIPRR is picking it up</> : 'A little appreciation, one post away.'}</div>}
    <div className="demo-bottom"><div className="demo-asset-tabs">{examples.map((e, i) => <button key={i} data-testid={`demo-asset-${i}`} className={i === example ? 'selected' : ''} onClick={() => { setExample(i); setTick(0); }}>{e.amount.split(' ')[1]}</button>)}</div><span data-testid="demo-bottom-note">one command. good energy.</span></div>
  </div>;
};