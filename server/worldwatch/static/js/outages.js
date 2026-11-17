// Country-level internet outage signals from IODA (Georgia Tech). A country has no single point, so each
// marker sits at the country's geographic centre; the card says so.
import {ago, esc, local, now, utc, countryBtn} from './util.js';
import {radarStale} from './netwatch.js';

const SRC = 'ww-outages';
let events = [], info = null, notes = [], radarInfo = null;   // notes: Cloudflare Radar's written outage annotations
const CAUSE_K = {POWER_OUTAGE: 'P', MILITARY_ACTION: 'M', CABLE_CUT: 'C', GOVERNMENT_DIRECTED: 'G', CYBERATTACK: 'X', NATURAL_DISASTER: 'N', WEATHER: 'W'};
const noteAt = n => n.countries.find(c => c.at)?.at;
// a note without an end is "ongoing" only while the Cloudflare feed is alive; from a stopped feed it is "no end noted
// when last read", is not counted and faded (a dead feed is shown as dead)
const open = n => !n.end && !radarStale(radarInfo);
const noteState = n => n.end ? 'ended ' + ago(n.end) : radarStale(radarInfo) ? `no end noted when last read ${ago(radarInfo?.fetched)} (feed stopped)` : 'ongoing';
const SIGNALS = {bgp: 'routing announcements (BGP)', 'ping-slash24': 'active probing', 'merit-nt': 'network telescope traffic', gtr: 'Google traffic', 'gtr-norm': 'Google traffic'};
const ends = e => e.start + e.duration_s;
const span = s => s < 5400 ? Math.round(s / 60) + ' min' : s < 172800 ? (s / 3600).toFixed(1) + ' h' : Math.round(s / 86400) + ' days';

export default {
  id: 'outages', title: 'Outages', color: ['#636366', '#aeaeb2'], feeds: {outages: 120, cf_radar: 600}, layers: ['ww-outages', 'ww-outages-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    // size follows IODA's own score (log scale), faded once the outage has ended; Cloudflare notes are small with a cause letter
    map.addLayer({id: 'ww-outages', type: 'circle', source: SRC, layout: {'circle-sort-key': ['coalesce', ['get', 'mag'], 0]},
      paint: {'circle-radius': ['case', ['has', 'k'], 9, ['interpolate', ['linear'], ['coalesce', ['get', 'mag'], 0], 0, 9, 3, 11, 6, 15, 9, 20]],
        'circle-opacity': ['case', ['==', ['get', 'over'], true], 0.45, 0.95], 'circle-stroke-width': ['case', ['==', ['get', 'over'], true], 0.8, 1.6]}});
    map.addLayer({id: 'ww-outages-label', type: 'symbol', source: SRC,
      layout: {'text-field': ['coalesce', ['get', 'k'], ['get', 'cc'], '!'], 'text-font': ['Noto Sans Bold'], 'text-size': ['case', ['has', 'k'], 12, 10.5], 'text-allow-overlap': true, 'text-ignore-placement': true}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-outages', 'circle-color', ['case', ['has', 'k'], dark ? '#ff9f0a' : '#c93400', this.color[+dark]]);
    map.setPaintProperty('ww-outages', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-outages-label', 'text-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { if (feed === 'cf_radar') { notes = d.payload.outages || []; radarInfo = d; } else { events = d.payload.events; info = d; } },
  render(map) {
    const seen = new Set();   // one marker per country, even when several signals report it
    // per country the strongest signal decides the size; "over" only when every signal for the country has ended
    const byCc = {};
    for (const e of events) if (e.lon != null) { const b = byCc[e.code] ||= {e, score: 0, live: false}; if (e.score > b.score) { b.score = e.score; b.e = e; } if (ends(e) >= now() - 900) b.live = true; }
    map.getSource(SRC).setData({type: 'FeatureCollection', features: Object.entries(byCc).map(([cc, b]) => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [b.e.lon, b.e.lat]}, properties: {id: b.e.id, cc: String(cc).toUpperCase().slice(0, 3), mag: Math.log10(Math.max(1, b.score)), over: !b.live}})).concat(
      // Cloudflare's notes: one marker per note and country, a little off the IODA marker so both can be clicked
      notes.filter(n => !n.end || n.end > now() - 7 * 86400).flatMap(n => n.countries.filter(c => c.at).map(c => ({type: 'Feature',
        geometry: {type: 'Point', coordinates: [c.at[0] + 1.2, c.at[1] - 0.8]}, properties: {id: 'cfnote:' + n.id, k: CAUSE_K[n.cause_code] || 'i', over: !open(n)}}))))});
  },
  count: () => new Set(events.map(e => e.code)).size + notes.filter(open).length,
  rows() {
    return events.map(e => ({id: e.id, time: e.start, badge: String(e.code || '!').toUpperCase().slice(0, 3), title: `Internet disruption, ${e.where}`,
      meta: `${ends(e) < now() - 900 ? 'Ended ' + ago(ends(e)) : 'Ongoing, ' + span(e.duration_s)} · ${SIGNALS[e.signal] || e.signal} · IODA`})).concat(notes.filter(n => !n.end || n.end > now() - 7 * 86400).map(n => ({
      id: 'cfnote:' + n.id, time: n.start, badge: CAUSE_K[n.cause_code] || 'i', strong: ['MILITARY_ACTION', 'GOVERNMENT_DIRECTED', 'CABLE_CUT'].includes(n.cause_code),
      title: n.text, meta: `${n.cause ? n.cause[0].toUpperCase() + n.cause.slice(1) : 'Outage'} · ${noteState(n)} · Cloudflare Radar`})));
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
          <dt>${n.end ? 'Ended' : 'Status'}</dt><dd>${n.end ? local(n.end) + ` <span class="soft">(${ago(n.end)})</span>` : radarStale(radarInfo) ? esc(noteState(n)) : 'ongoing, as far as Cloudflare has noted'}</dd>
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
