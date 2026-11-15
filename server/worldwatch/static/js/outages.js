// Country-level internet outage signals from IODA (Georgia Tech). A country has no single point, so each
// marker sits at the country's geographic centre; the card says so.
import {ago, esc, local, now, utc, countryBtn} from './util.js';

const SRC = 'ww-outages';
let events = [], info = null;
const SIGNALS = {bgp: 'routing announcements (BGP)', 'ping-slash24': 'active probing', 'merit-nt': 'network telescope traffic', gtr: 'Google traffic', 'gtr-norm': 'Google traffic'};
const ends = e => e.start + e.duration_s;
const span = s => s < 5400 ? Math.round(s / 60) + ' min' : s < 172800 ? (s / 3600).toFixed(1) + ' h' : Math.round(s / 86400) + ' days';

export default {
  id: 'outages', title: 'Outages', color: ['#636366', '#aeaeb2'], feeds: {outages: 120}, layers: ['ww-outages', 'ww-outages-label'],

  addTo(map) {
    map.addSource(SRC, {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-outages', type: 'circle', source: SRC, paint: {'circle-radius': 9, 'circle-opacity': 0.92, 'circle-stroke-width': 1.2}});
    map.addLayer({id: 'ww-outages-label', type: 'symbol', source: SRC,
      layout: {'text-field': '!', 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-allow-overlap': true, 'text-ignore-placement': true}});
  },
  paint(map, dark) {
    map.setPaintProperty('ww-outages', 'circle-color', this.color[+dark]);
    map.setPaintProperty('ww-outages', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
    map.setPaintProperty('ww-outages-label', 'text-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, d) { events = d.payload.events; info = d; },
  render(map) {
    const seen = new Set();   // one marker per country, even when several signals report it
    map.getSource(SRC).setData({type: 'FeatureCollection', features: events.filter(e => e.lon != null && !seen.has(e.code) && seen.add(e.code)).map(e => (
      {type: 'Feature', geometry: {type: 'Point', coordinates: [e.lon, e.lat]}, properties: {id: e.id}}))});
  },
  count: () => new Set(events.map(e => e.code)).size,
  rows() {
    return events.map(e => ({id: e.id, time: e.start, badge: '!', title: `Internet disruption, ${e.where}`,
      meta: `Outage signal · started ${local(e.start)} · ${ago(e.start)}`}));
  },
  locate(id) { const e = events.find(x => x.id === id); return e && e.lon != null ? [e.lon, e.lat] : null; },
  ring: () => 15,
  detail(id) {
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
