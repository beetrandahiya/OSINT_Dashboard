// Country-level internet outage signals from IODA (Georgia Tech). A country has no single point, so each
// marker sits at the country's geographic centre; the card says so.
import {ago, esc, local, now, utc, countryBtn} from './util.js';

const SRC = 'ww-outages';
let events = [], info = null, notes = [], radarInfo = null;   // notes: Cloudflare Radar's written outage annotations
const CAUSE_K = {POWER_OUTAGE: 'P', MILITARY_ACTION: 'M', CABLE_CUT: 'C', GOVERNMENT_DIRECTED: 'G', CYBERATTACK: 'X', NATURAL_DISASTER: 'N', WEATHER: 'W'};
const noteAt = n => n.countries.find(c => c.at)?.at;
const SIGNALS = {bgp: 'routing announcements (BGP)', 'ping-slash24': 'active probing', 'merit-nt': 'network telescope traffic', gtr: 'Google traffic', 'gtr-norm': 'Google traffic'};
const ends = e => e.start + e.duration_s;
const span = s => s < 5400 ? Math.round(s / 60) + ' min' : s < 172800 ? (s / 3600).toFixed(1) + ' h' : Math.round(s / 86400) + ' days';

export default {
  id: 'outages', title: 'Outages', color: ['#636366', '#aeaeb2'], feeds: {outages: 120, cf_radar: 600}, layers: ['ww-outages', 'ww-outages-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-outages', type: 'circle', source: SRC, paint: {'circle-radius': 9, 'circle-opacity': 0.92, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-outages-label', type: 'symbol', source: SRC,
      layout: {'text-field': ['coalesce', ['get', 'k'], '!'], 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-allow-overlap': true, 'text-ignore-placement': true}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-outages', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-outages', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-outages-label', 'text-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { if (feed === 'cf_radar') { notes = d.payload.outages || []; radarInfo = d; } else { events = d.payload.events; info = d; } },
  render(map) {
    const seen = new Set();   // one marker per country, even when several signals report it
    map.getSource(SRC).setData({type: 'FeatureCollection', features: events.filter(e => e.lon != null && !seen.has(e.code) && seen.add(e.code)).map(e => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [e.lon, e.lat]}, properties: {id: e.id}})).concat(
      // Cloudflare's notes: one marker per note and country, a little off the IODA marker so both can be clicked
      notes.filter(n => !n.end || n.end > now() - 7 * 86400).flatMap(n => n.countries.filter(c => c.at).map(c => ({type: 'Feature',
        geometry: {type: 'Point', coordinates: [c.at[0] + 1.2, c.at[1] - 0.8]}, properties: {id: 'cfnote:' + n.id, k: CAUSE_K[n.cause_code] || 'i'}}))))});
  },
  count: () => new Set(events.map(e => e.code)).size + notes.filter(n => !n.end).length,
  rows() {
    return events.map(e => ({id: e.id, time: e.start, badge: '!', title: `Internet disruption, ${e.where}`,
      meta: `Outage signal · started ${local(e.start)} · ${ago(e.start)}`})).concat(notes.filter(n => !n.end || n.end > now() - 7 * 86400).map(n => ({
      id: 'cfnote:' + n.id, time: n.start, badge: CAUSE_K[n.cause_code] || 'i', strong: ['MILITARY_ACTION', 'GOVERNMENT_DIRECTED', 'CABLE_CUT'].includes(n.cause_code),
      title: n.text, meta: `${n.cause ? n.cause[0].toUpperCase() + n.cause.slice(1) : 'Outage'} · ${n.end ? 'ended ' + ago(n.end) : 'ongoing'} · Cloudflare Radar`})));
  },
  locate(id) {
    if (String(id).startsWith('cfnote:')) { const n = notes.find(x => 'cfnote:' + x.id === id), a = n && noteAt(n); return a ? [a[0] + 1.2, a[1] - 0.8] : null; }
    const e = events.find(x => x.id === id); return e && e.lon != null ? [e.lon, e.lat] : null;
  },
  ring: () => 15,
  owns: id => String(id).startsWith('cfnote:') || events.some(e => e.id === id),
  detail(id) {
    if (String(id).startsWith('cfnote:')) {
      const n = notes.find(x => 'cfnote:' + x.id === id); if (!n) return null;
      return `<p class="eyebrow">Internet outage · Cloudflare's note</p>
        <h2>${esc(n.countries.map(c => c.name).join(', ') || 'Outage')}</h2>
        <p class="where">${esc(n.cause ? n.cause[0].toUpperCase() + n.cause.slice(1) : 'Cause not given')}${n.scope ? ' · ' + esc(n.scope) : ''}</p>
        <p>${esc(n.text || '')}</p>
        <dl><dt>Started</dt><dd>${local(n.start)} <span class="soft">(${ago(n.start)})</span></dd>
          <dt>${n.end ? 'Ended' : 'Status'}</dt><dd>${n.end ? local(n.end) + ` <span class="soft">(${ago(n.end)})</span>` : 'ongoing, as far as Cloudflare has noted'}</dd>
          ${n.regions.length ? `<dt>Regions</dt><dd>${n.regions.map(esc).join(', ')}</dd>` : ''}
          ${n.networks.length ? `<dt>Networks</dt><dd>${n.networks.map(esc).join(', ')}</dd>` : ''}</dl>
        ${n.countries[0] ? countryBtn({cc: n.countries[0].cc}) : ''}
        ${n.link ? `<a class="link" href="${esc(n.link)}" target="_blank" rel="noopener">Cloudflare's post about it</a>` : ''}
        <a class="link" href="https://radar.cloudflare.com/outage-center" target="_blank" rel="noopener">Cloudflare Radar outage center</a>
        <p class="source">Source: Cloudflare Radar's outage annotations (CC BY-NC 4.0), written by Cloudflare from its own traffic data; read ${ago(radarInfo?.fetched)}. The cause is theirs. The marker sits next to the country's centre.</p>`;
    }
    const e = events.find(x => x.id === id);
    if (!e) return null;
    const others = events.filter(x => x.code === e.code && x.id !== e.id);
    const over = ends(e) < now() - 900;
    return `<p class="eyebrow">Internet outage signal</p>
      <h2>${esc(e.where)}</h2>
      <p class="where">Country-level signal</p>
      <dl>
        <dt>Started</dt><dd>${local(e.start)} <span class="soft">(${utc(e.start)}, ${ago(e.start)})</span></dd>
        <dt>${over ? 'Lasted' : 'Lasting so far'}</dt><dd>${span(e.duration_s)}${over ? ` <span class="soft">(ended ${ago(ends(e))})</span>` : ''}</dd>
        <dt>Seen in</dt><dd>${esc(SIGNALS[e.signal] || e.signal)}</dd>
        <dt>IODA's own score</dt><dd>${Math.round(e.score).toLocaleString('en-GB')} <span class="soft">(theirs, unitless)</span></dd>
      </dl>
      ${others.length ? `<p class="source">${others.length} more ${others.length === 1 ? 'signal' : 'signals'} for this country in the last 24 hours.</p>` : ''}
      ${countryBtn({cc: e.code})}
      <a class="link" href="https://ioda.inetintel.cc.gatech.edu/country/${esc(e.code)}" target="_blank" rel="noopener">Open this country on IODA</a>
      <p class="source">Source: IODA, Georgia Tech; fetched ${ago(info.fetched)}. A signal means IODA measured a drop; it does not say why, or how many people are affected. The marker sits at the country's centre, not at the fault.</p>`;
  },
};
