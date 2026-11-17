// The markets strip: a few numbers, each with its own age. Yahoo's quotes are unofficial and delayed;
// the change is simply the price against the previous close that Yahoo itself reports.
import {every} from './prefs.js';
import {$, ago, api, esc} from './util.js';

const SHORT = {'^GSPC': 'S&P 500', '^GDAXI': 'DAX', '^N225': 'Nikkei', '^NSEI': 'Nifty 50', 'BZ=F': 'Brent', 'GC=F': 'Gold', 'EURUSD=X': 'EUR/USD'};
const num = (v, d = 2) => v.toLocaleString('en-GB', {minimumFractionDigits: d, maximumFractionDigits: d});
const pct = c => `<span class="${c >= 0 ? 'up' : 'down'}">${c >= 0 ? '+' : '−'}${Math.abs(c).toFixed(2)}%</span>`;
let got = {};

async function load(name) { try { got[name] = await api('/api/data/' + name); } catch (e) { /* the feeds card reports failures */ } }

function render() {
  const out = [], m = got.markets, c = got.crypto, f = got.fx;
  if (m?.payload) for (const q of m.payload.quotes) {
    const ch = q.previous_close ? (q.price / q.previous_close - 1) * 100 : null;
    out.push(`<span class="quote" title="${esc(q.exchange || '')} via Yahoo Finance, unofficial and delayed. Change is against the previous close.">
      <b>${SHORT[q.symbol] || esc(q.name)}</b>${num(q.price, q.symbol === 'EURUSD=X' ? 4 : 2)} ${ch == null ? '' : pct(ch)}<i>${ago(q.time)}</i></span>`);
  }
  if (c?.payload) { const b = c.payload.bitcoin;
    out.push(`<span class="quote" title="CoinGecko. Change is over 24 hours, as CoinGecko reports it."><b>Bitcoin</b>$${num(b.usd, 0)} ${b.usd_24h_change == null ? '' : pct(b.usd_24h_change)}<i>${ago(b.last_updated_at)}</i></span>`); }
  if (f?.payload?.rates?.INR) out.push(`<span class="quote" title="European Central Bank reference rate, published once per working day."><b>EUR/INR</b>${num(f.payload.rates.INR)}<i>ECB, ${esc(f.payload.date.slice(5).split('-').reverse().join('.'))}</i></span>`);
  $('#markets').innerHTML = out.join('') || '<span class="quote"><i>No market data yet</i></span>';
}

export function start() {
  const go = async () => { await Promise.all(['markets', 'crypto', 'fx'].map(load)); render(); };
  go(); every(60, go); every(20, render, {scaled: false});
}
