// Internet routing incidents from Cloudflare Radar: BGP hijacks (a network announcing address blocks that belong to
// another) and route leaks, last 24 hours. Networks have no position: lines join the countries Cloudflare gives for
// the networks, drawn between country centres. See radar.py.
import {ago, esc, local, countryBtn} from './util.js';
import {flagImg} from './flags.js';

let d = {hijacks: [], leaks: []}, info = null;
const LIST_MIN = 10;
const net = n => `${esc(n.org || 'unknown network')} <span class="soft">(AS${n.asn}${n.cc ? ', ' + esc(n.cc) : ''})</span>`;
const strong = h => (h.score ?? 0) >= LIST_MIN;

export default {
  id: 'hijacks', title: 'Internet hijacks', color: ['#d70015', '#ff6961'], feeds: {cf_radar: 600},
  layers: ['ww-bgp-leak', 'ww-bgp-line', 'ww-bgp-dot'],
  about: () => 'BGP hijacks and route leaks of the last 24 hours, from Cloudflare Radar.',
  addTo(map) {
    map.addSource('ww-bgp', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
    map.addLayer({id: 'ww-bgp-leak', type: 'line', source: 'ww-bgp', filter: ['==', ['get', 'kind'], 'leak'],
      paint: {'line-width': 1, 'line-opacity': 0.35, 'line-dasharray': [2, 3]}});
    map.addLayer({id: 'ww-bgp-line', type: 'line', source: 'ww-bgp', filter: ['==', ['get', 'kind'], 'hijack'],
      paint: {'line-width': ['case', ['get', 'strong'], 2, 1], 'line-opacity': ['case', ['get', 'strong'], 0.9, 0.35]}});
    map.addLayer({id: 'ww-bgp-dot', type: 'circle', source: 'ww-bgp', filter: ['==', ['geometry-type'], 'Point'],
      paint: {'circle-radius': ['case', ['get', 'strong'], 6, 3.5], 'circle-stroke-width': 1.2, 'circle-opacity': ['case', ['get', 'strong'], 1, 0.6]}});
  },
  paint(map, dark) {
    const c = this.color[+dark], soft = dark ? '#aeaeb2' : '#8e8e93';
    map.setPaintProperty('ww-bgp-line', 'line-color', ['case', ['get', 'strong'], c, soft]);
    map.setPaintProperty('ww-bgp-leak', 'line-color', dark ? '#64d2ff' : '#0071a4');
    map.setPaintProperty('ww-bgp-dot', 'circle-color', ['case', ['get', 'strong'], c, soft]);
    map.setPaintProperty('ww-bgp-dot', 'circle-stroke-color', dark ? '#1c1c1e' : '#ffffff');
  },
  onData(feed, x) { d = x.payload; info = x; },
  render(map) {
    const f = [];
    for (const h of d.hijacks) {
      const a = h.hijacker.at; if (!a) continue;
      const props = {id: 'bgp:' + h.id, kind: 'hijack', strong: strong(h)};
      for (const v of h.victim_countries) if (v.at && v.cc !== h.hijacker.cc) f.push({type: 'Feature', geometry: {type: 'LineString', coordinates: [a, v.at]}, properties: props});
      f.push({type: 'Feature', geometry: {type: 'Point', coordinates: a}, properties: props});
    }
    for (const l of d.leaks) {
      const pts = l.countries.map(c => c.at).filter(Boolean);
      if (pts.length >= 2) f.push({type: 'Feature', geometry: {type: 'LineString', coordinates: pts}, properties: {id: 'leak:' + l.id, kind: 'leak'}});
    }
    map.getSource('ww-bgp').setData({type: 'FeatureCollection', features: f});
  },
  count: () => d.hijacks.filter(strong).length,
  rows: () => d.hijacks.filter(strong).map(h => ({id: 'bgp:' + h.id, time: h.start, badge: '⇄', strong: (h.score ?? 0) >= 12,
    title: `${h.hijacker.org || 'AS' + h.hijacker.asn} announced ${h.prefix_count} address ${h.prefix_count === 1 ? 'block' : 'blocks'} of ${h.victims.map(v => v.org || 'AS' + v.asn).join(', ')}`,
    meta: `Possible hijack · ${h.hijacker.cc || '?'} → ${h.victim_countries.map(v => v.cc).join(', ') || '?'} · score ${h.score} · ${ago(h.start)}`})),
  owns: id => /^(bgp|leak):/.test(String(id)),
  locate(id) {
    if (String(id).startsWith('leak:')) return d.leaks.find(x => 'leak:' + x.id === id)?.countries.find(c => c.at)?.at || null;
    return d.hijacks.find(x => 'bgp:' + x.id === id)?.hijacker.at || null;
  },
  ring: () => 12,
  detail(id) {
    const src = `<p class="source">Source: Cloudflare Radar (CC BY-NC 4.0), read ${ago(info?.fetched)}. Detected from routing announcements Cloudflare's collectors saw; a "hijack" here means the announcement looks wrong, which also happens by mistake or when a customer's provider announces for it. Lines join the countries Cloudflare lists for the networks, drawn between country centres; networks have no single place.</p>`;
    if (String(id).startsWith('leak:')) {
      const l = d.leaks.find(x => 'leak:' + x.id === id); if (!l) return null;
      return `<p class="eyebrow">Route leak</p><h2>${esc(l.leaker.org || 'AS' + l.leaker.asn)}</h2>
        <p class="where">passed on routes it should not have, ${l.finished ? 'finished' : 'still going'}</p>
        <dl><dt>Path</dt><dd>${l.path.map(net).join(' → ')}</dd><dt>Countries</dt><dd>${l.countries.map(c => flagImg(c.cc) + ' ' + esc(c.cc)).join(' · ')}</dd>
          <dt>Address blocks</dt><dd>${l.prefixes}</dd><dt>Seen</dt><dd>${local(l.start)}${l.last && l.last !== l.start ? ' to ' + local(l.last) : ''}</dd></dl>
        <p class="soft">A leak sends other networks' traffic the wrong way, usually by mistake. Over 400 happen on a normal day; only the 40 involving the most address blocks across a border are drawn.</p>${src}`;
    }
    const h = d.hijacks.find(x => 'bgp:' + x.id === id); if (!h) return null;
    return `<p class="eyebrow">Possible BGP hijack · score ${h.score}</p>
      <h2>${esc(h.hijacker.org || 'AS' + h.hijacker.asn)} ${h.hijacker.cc ? flagImg(h.hijacker.cc) : ''}</h2>
      <p class="where">announced address blocks that belong to ${h.victims.map(v => esc(v.org || 'AS' + v.asn)).join(', ')}</p>
      <dl>
        <dt>Announced by</dt><dd>${net(h.hijacker)}</dd>
        <dt>Belongs to</dt><dd>${h.victims.map(net).join('<br>')}</dd>
        <dt>Address blocks</dt><dd>${h.prefixes.map(esc).join(', ')}${h.prefix_count > h.prefixes.length ? ` and ${h.prefix_count - h.prefixes.length} more` : ''}</dd>
        <dt>When</dt><dd>${local(h.start)}${h.duration_s ? `, lasted ${Math.round(h.duration_s / 60)} min` : ', a single announcement'}${h.ongoing ? ' <span class="soft">(still announced)</span>' : ''}</dd>
        <dt>Seen by</dt><dd>${h.seen_by_peers ?? '?'} of Cloudflare's peers</dd>
      </dl>
      <section class="pz"><h3>Why Cloudflare flags it (score ${h.score})</h3>${h.evidence.length ? `<ul class="dos-list">${h.evidence.map(e => `<li>${esc(e)}</li>`).join('')}</ul>` : '<p class="soft">No evidence tags.</p>'}
        <p class="soft">The score is the sum of these signs (8 for RPKI, 4 for the registries); we list 10 and above. A high score says the announcement is not authorised, not who meant what.</p></section>
      ${h.victim_countries[0] ? countryBtn({cc: h.victim_countries[0].cc}, 'Dossier of the victim\'s country') : ''}
      <a class="link" href="https://radar.cloudflare.com/routing" target="_blank" rel="noopener">Cloudflare Radar routing</a>${src}`;
  },
};
