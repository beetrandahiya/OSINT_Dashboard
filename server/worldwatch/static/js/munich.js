// The Munich view: what is overhead, the weather, official warnings, and public transport disruptions.
import {$, ago, api, esc, local} from './util.js';

let got = {}, home = {lat: 48.137, lon: 11.575}, onPick = () => {}, active = false;
const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
const CONDITION = {dry: 'Dry', fog: 'Fog', rain: 'Rain', sleet: 'Sleet', snow: 'Snow', hail: 'Hail', thunderstorm: 'Thunderstorm'};
const TRANSPORT = {SBAHN: 'S-Bahn', UBAHN: 'U-Bahn', TRAM: 'Tram', BUS: 'Bus', REGIONAL_BUS: 'Regional bus', BAHN: 'Train'};

function from(a) {   // distance in km and compass direction from home to an aircraft
  const r = Math.PI / 180, dLat = (a.lat - home.lat) * r, dLon = (a.lon - home.lon) * r, la1 = home.lat * r, la2 = a.lat * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
  const b = Math.atan2(Math.sin(dLon) * Math.cos(la2), Math.cos(la1) * Math.sin(la2) - Math.sin(la1) * Math.cos(la2) * Math.cos(dLon)) / r;
  return {km: 12742 * Math.asin(Math.sqrt(h)), dir: COMPASS[Math.round(((b + 360) % 360) / 45) % 8]};
}

async function load(name) { try { got[name] = await api('/api/data/' + name); } catch (e) { /* the feeds card reports failures */ } }

function render() {
  const el = $('#munich'); if (!el || !active) return;
  const w = got.munich_weather, air = got.aircraft_near, m = got.mvg;
  let html = '';

  html += '<h3>Now</h3>';
  if (w?.payload) {
    const n = w.payload.now;
    html += `<div class="m-now"><b>${n.temperature == null ? '?' : n.temperature.toFixed(1)} °C</b><span>${esc(CONDITION[n.condition] || n.condition || '')}</span></div>
      <p class="m-line">Wind ${Math.round(n.wind_speed_10)} km/h from the ${COMPASS[Math.round(n.wind_direction_10 / 45) % 8]}, gusts ${Math.round(n.wind_gust_speed_10)} km/h · humidity ${n.relative_humidity} % · cloud ${n.cloud_cover} %</p>
      <p class="m-src">German Weather Service station ${esc(w.payload.station || '')}, measured ${local(w.payload.observed)} (${ago(w.payload.observed)})</p>`;
    html += '<h3>Official warnings</h3>';
    html += w.payload.alerts.length ? w.payload.alerts.map(a => `<div class="m-item"><b>${esc(a.headline || a.event || 'Warning')}</b>
        <span>${esc((a.description || '').replace(/\s+/g, ' '))}</span>
        <span class="soft">${a.onset ? 'From ' + local(a.onset) : ''}${a.expires ? ' to ' + local(a.expires) : ''}${a.severity ? ' · severity ' + esc(a.severity) : ''}</span></div>`).join('')
      : '<p class="m-line">None in force for Munich.</p>';
    html += '<p class="m-src">German Weather Service via Bright Sky</p>';
  } else html += '<p class="m-line">Weather not loaded yet.</p>';

  html += '<h3>Overhead now</h3>';
  if (air?.payload) {
    const near = air.payload.aircraft.filter(a => a.alt_ft !== 'ground' && a.alt_ft != null).map(a => ({a, ...from(a)})).sort((x, y) => x.km - y.km).slice(0, 8);
    html += near.length ? '<ul class="m-air">' + near.map(({a, km, dir}) => `<li tabindex="0" data-hex="${esc(a.hex)}"><b>${esc(a.flight || a.reg || a.hex.toUpperCase())}</b>
        <span>${esc(a.type || '')}</span><span class="r">${km < 10 ? km.toFixed(1) : Math.round(km)} km ${dir} · ${Number(a.alt_ft).toLocaleString('en-GB')} ft</span></li>`).join('') + '</ul>' : '<p class="m-line">No aircraft in the air nearby.</p>';
    html += `<p class="m-src">Nearest airborne aircraft to the city centre, from adsb.fi, data ${ago(air.data_time)}. Distance is along the ground, not line of sight.</p>`;
  } else html += '<p class="m-line">Aircraft not loaded yet.</p>';

  html += '<h3>Public transport</h3>';
  if (m?.payload) {
    const msgs = m.payload.messages, show = msgs.slice(0, 8);
    html += m.payload.incidents ? '' : '<p class="m-line">No incidents reported right now.</p>';
    html += show.map(x => `<div class="m-item${x.kind === 'INCIDENT' ? ' incident' : ''}"><b>${x.kind === 'INCIDENT' ? 'Incident: ' : ''}${esc(x.title || '')}</b>
        ${x.title_original ? `<span class="soft">${esc(x.title_original)}</span>` : ''}
        <span class="soft">${esc([...new Set(x.transport.map(t => TRANSPORT[t] || t))].join(', '))}${x.lines.length ? ' · ' + esc(x.lines.slice(0, 8).join(', ')) + (x.lines.length > 8 ? ' and more' : '') : ''} · ${x.kind === 'INCIDENT' ? 'since ' + local(x.from) : 'planned change'}</span></div>`).join('');
    if (msgs.length > show.length) html += `<p class="m-line">${msgs.length - show.length} more planned changes in force.</p>`;
    html += `<a class="link" href="https://www.mvg.de/meldungen.html" target="_blank" rel="noopener">All messages on mvg.de</a>
      <p class="m-src">From the feed behind mvg.de, fetched ${ago(m.fetched)}. It is not an official public service and may stop working. English headlines are machine-translated.</p>`;
  } else html += '<p class="m-line">Transport messages not loaded yet.</p>';

  if (el.dataset.html !== html && !el.matches(':hover')) { const y = el.scrollTop; el.innerHTML = html; el.dataset.html = html; el.scrollTop = y; }
  else if (!el.dataset.html) { el.innerHTML = html; el.dataset.html = html; }
}

export function start(pick) {
  onPick = pick;
  api('/api/status').then(s => { if (s.home) home = s.home; }).catch(() => {});
  const go = async () => { if (!active) return; await Promise.all(['munich_weather', 'mvg', 'aircraft_near'].map(load)); render(); };
  setInterval(go, 20000);
  $('#munich').addEventListener('click', e => { const li = e.target.closest('li[data-hex]'); if (li) onPick(li.dataset.hex); });
  $('#munich').addEventListener('keydown', e => { const li = e.target.closest('li[data-hex]'); if (li && e.key === 'Enter') onPick(li.dataset.hex); });
  return {
    show(on) { active = on; if (on) { render(); go(); } },
    home: () => home,
  };
}
