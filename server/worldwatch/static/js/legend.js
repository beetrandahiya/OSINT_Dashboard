// The legend: what each symbol on the map means, for the layers that are switched on. Colours and letters are the
// same ones the layers paint with (light, dark); keep them in step when a layer's look changes.
import {eyeOn, glyphSvg} from './eyeicons.js';
import {esc} from './util.js';

const L = (light, dark) => d => d ? dark : light;
const BROWN = L('#a2845e', '#ac8e68'), RED = L('#d70015', '#ff6961'), ORANGE = L('#c93400', '#ff9f0a'), GREY = L('#8e8e93', '#aeaeb2'), EDGE = L('#ffffff', '#1c1c1e');
// shapes: dot, ring, halo (soft fill + ring), letter (dot with a letter), ringletter, line, dash, area, plane, diamond, ship
const LEGENDS = {
  hotspots: [['letter', L('#ff2d55', '#ff375f'), 'Hotspot: number = kinds of security signal within 250 km in a day', '3'], ['halo', L('#ff2d55', '#ff375f'), 'The 250 km area the signals fall in']],
  news: [['halo', L('#ff3b30', '#ff453a'), 'Group of nearby places (number = places; zoom in to split)'],
    ['letter', L('#ff3b30', '#ff453a'), 'A place in the news; size and number = different outlets, last 6 h', '12'],
    ['dot', L('#ff3b30', '#ff453a'), 'Faint: only 1 or 2 outlets', '', 0.4]],
  spikes: [['halo', RED, 'Sudden jump in reporting in the newest hour (at least 3 times its usual rate)']],
  unrest: [['ringletter', BROWN, 'Protest', 'P'], ['letter', BROWN, 'Riot', 'R'], ['letter', BROWN, 'Attack', 'A'], ['letter', BROWN, 'Armed clash', 'C'],
    ['letter', BROWN, 'Mass violence', 'M'], ['note', null, 'Size = number of outlets. Machine-coded from news, not verified.']],
  unrest1: [['letter', BROWN, 'Reported by one outlet only (faint)', 'P', 0.55]],
  front: [['area', RED, 'Occupied (DeepState\'s assessment)'], ['area', GREY, 'Status unclear'], ['ring', L('#b25000', '#ffd60a'), 'Change in the latest update'],
    ['letter', RED, 'Russian unit position (from zoom 6)', 'U'], ['letter', ORANGE, 'Direction of attack', '➜'], ['letter', L('#3a3a3c', '#636366'), 'Airfield / headquarters', 'A']],
  navwarn: [['dash', L('#c9a400', '#ffd60a'), 'Warning area as the notice describes it'], ['letter', L('#c9a400', '#ffd60a'), 'Rocket or space debris', 'R'],
    ['letter', L('#c9a400', '#ffd60a'), 'Missile firing', 'M'], ['letter', L('#c9a400', '#ffd60a'), 'Weapons firing or explosives', 'W'],
    ['letter', L('#c9a400', '#ffd60a'), 'Military exercise', 'X'], ['letter', L('#c9a400', '#ffd60a'), 'Security threat', 'S'], ['letter', L('#c9a400', '#ffd60a'), 'GPS / GNSS interference', 'G']],
  airspace: [['area', RED, 'Flight region under a conflict-zone warning (stronger = "do not operate")'], ['line', RED, 'US temporary flight restriction (exact shape)']],
  quakes: [['letter', L('#ff9500', '#ff9f0a'), 'Earthquake; number = magnitude, size grows with it', '4.5'], ['note', null, '☢ in the list: within 50 km of a nuclear test site']],
  hazards: [['letter', L('#ff2d55', '#ff375f'), 'Tropical cyclone (larger = GDACS orange / red alert)', 'C'], ['letter', L('#ff2d55', '#ff375f'), 'Flood', 'F'],
    ['letter', L('#ff2d55', '#ff375f'), 'Volcano', 'V'], ['letter', L('#ff2d55', '#ff375f'), 'Drought', 'D'], ['letter', L('#ff2d55', '#ff375f'), 'Wildfire', 'W'],
    ['letter', L('#ff2d55', '#ff375f'), 'Sea and lake ice / landslide / dust and haze', 'I'], ['line', L('#ff2d55', '#ff375f'), 'Storm track']],
  outages: [['letter', L('#636366', '#aeaeb2'), 'Country with an internet outage signal (IODA); size = IODA\'s score', 'IR'],
    ['letter', L('#636366', '#aeaeb2'), 'Faint: the outage has ended', 'IR', 0.45],
    ['letter', ORANGE, 'Cloudflare\'s note; letter = cause: P power, M military, C cable cut, G government, X cyberattack, N natural disaster, W weather', 'C']],
  hijacks: [['streak', RED, 'Possible BGP hijack, from the announcing network\'s country to the victim\'s (Cloudflare score 10 or more)'],
    ['streak', ORANGE, 'Weaker hijack signal'], ['dash', L('#0071a4', '#64d2ff'), 'Route leak'], ['note', null, 'The streaks show direction, not live traffic.']],
  bases: [['dot', L('#6e4f2d', '#c8a37a'), 'Military base, airfield or naval base'], ['dot', L('#c4161c', '#ff6961'), 'Missile or signals-intelligence site'],
    ['dot', L('#b25000', '#ffb340'), 'Military radar'], ['ringdot', L('#6e4f2d', '#c8a37a'), 'Military area (OpenStreetMap, unnamed, from zoom 7)']],
  nuclear: [['dot', L('#b8860b', '#ffd60a'), 'Nuclear power plant (faint = not operating)'], ['dot', ORANGE, 'Research reactor, fuel-cycle, waste or uranium site'],
    ['halo', RED, 'Nuclear test site'], ['dot', RED, 'Explosion point mapped by OpenStreetMap (from zoom 5)', '', 0.75]],
  aircraft: [['plane', L('#5856d6', '#7d7aff'), 'Aircraft; the shape follows what it broadcasts (airliner, heavy, prop, fighter, helicopter, drone...)'],
    ['note', null, 'Zoomed in: live positions (adsb.fi, 10 s). Zoomed out: OpenSky snapshot, up to 20 minutes old.'],
    ['dash', L('#5856d6', '#7d7aff'), 'Selected aircraft: straight line to the destination (not its planned path)'], ['line', L('#5856d6', '#7d7aff'), 'Path it really flew']],
  military: [['plane', L('#af52de', '#da8fff'), 'Military aircraft (adsb.fi, every 30 s)']],
  orbits: [['halo', RED, 'Surveillance aircraft flying an orbit (circling 2 h or more)'], ['halo', L('#8944ab', '#da8fff'), 'Other military aircraft in an orbit']],
  tankers: [['dot', L('#248a3d', '#30d158'), 'Tanker aircraft airborne']],
  vip: [['halo', L('#c69200', '#ffd426'), 'Government, royal or VIP aircraft (plane-alert-db); label = who it is listed with']],
  doomsday: [['halo', RED, 'Airborne command post ("doomsday plane")']],
  satellites: [['dot', L('#28a745', '#30d158'), 'Low Earth orbit (below 2,000 km)'], ['dot', L('#c98a00', '#ffc857'), 'Medium Earth orbit (navigation)'],
    ['dot', L('#007aff', '#7db7ff'), 'Geostationary (36,000 km)'], ['dot', L('#d6336c', '#ff7ab6'), 'Highly elliptical'], ['diamond', L('#ff3b30', '#ff453a'), 'Military imaging or signals satellite'],
    ['note', null, 'Letters on the globe: I imaging, R radar, S signals, W early warning, M weather, N navigation, C communications, X science, T technology']],
  launches: [['dot', L('#00a3b4', '#40c8e0'), 'Launch pad with a launch coming up'], ['area', L('#00a3b4', '#40c8e0'), 'Closure areas matched to the launch (TFRs, navy rocket warnings)']],
  ships: [['ship', L('#a2845e', '#c4a57b'), 'Ship, pointing the way it is heading'], ['line', L('#a2845e', '#c4a57b'), 'Selected ship: positions we received']],
  warships: [['ship', L('#636366', '#c7c7cc'), 'Warship broadcasting on AIS'], ['ring', L('#48484a', '#c7c7cc'), 'US carrier or amphibious ship (USNI); a wide ring = only the region is known']],
  sanctioned: [['letter', RED, 'Sanctioned or shadow-fleet ship', 'S'], ['letter', RED, 'Sanctioned aircraft', 'A']],
  cameras: [['dot', L('#0071a4', '#64d2ff'), 'Public traffic or weather camera'], ['dot', L('#248a3d', '#30d158'), 'Windy webcam with a live stream'],
    ['dot', L('#0a84ff', '#5ac8fa'), 'Windy webcam sending still pictures']],
  sdr: [['dot', L('#008a7a', '#40d9c4'), 'Public shortwave receiver you can tune in the browser'], ['dot', L('#008a7a', '#40d9c4'), 'Faint: all listener slots taken', '', 0.35]],
  people: [['dot', L('#ff9f0a', '#ffb340'), 'Head of state or government, at their country']],
  leaders: [['dot', L('#ff9f0a', '#ffb340'), 'Leader as placed by today\'s news (where reported, not a tracked location)'], ['dash', L('#ff9f0a', '#ffb340'), 'Abroad: line from home']],
  fires: [['dot', L('#ff5e3a', '#ff6a4d'), 'Hot spot seen by NASA\'s MODIS in the last 24 h (not always a wildfire)']],
  gps: [['area', L('#ff3b30', '#ff453a'), 'Over 10 % of aircraft reported poor GPS accuracy (GPSJAM, past day)'], ['area', L('#f5b800', '#ffd60a'), '2 to 10 %']],
  gpslive: [['area', L('#ff3b30', '#ff453a'), 'Over 10 % of aircraft with poor accuracy, last hour (our own count)'], ['area', L('#f5b800', '#ffd60a'), '2 to 10 %'],
    ['dash', L('#636366', '#aeaeb2'), 'Region we check']],
  cables: [['line', L('#6b7a8c', '#7d8a99'), 'Undersea cable'], ['line', L('#d70015', '#ff453a'), 'Named in fault or damage news'], ['line', L('#248a3d', '#30d158'), 'Reported repaired']],
  rain: [['gradient', null, 'Rain radar (RainViewer): darker and warmer colours mean heavier rain']],
  lightning: [['dot', L('#ff9f0a', '#ffb340'), 'Lightning in the last minutes (EUMETSAT; Europe, Africa, Atlantic)']],
  night: [['area', L('#1c1c1e', '#000000'), 'Night, fading through twilight']],
  aurora: [['area', L('#00a878', '#63e6be'), 'Where the aurora may be seen now (NOAA forecast)']],
  photo: [['note', null, 'Yesterday\'s satellite picture (NASA, NOAA-20 VIIRS, 375 m)']],
  livephoto: [['note', null, 'Geostationary satellite pictures, 10-15 minutes old (EUMETSAT, NOAA)']],
  sharp: [['note', null, 'Sharp aerial/satellite photo (Esri); the date of the picture under the map centre is shown on its chip']],
};

function swatch(shape, c, letter = '', alpha = 1) {
  const e = EDGE(isDark());
  const svg = inner => `<svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true" style="opacity:${alpha}">${inner}</svg>`;
  const t = letter ? `<text x="11" y="11.2" text-anchor="middle" font-size="${letter.length > 2 ? 6 : letter.length > 1 ? 7 : 8.5}" font-weight="700" fill="${shape === 'ringletter' ? c : '#fff'}" font-family="-apple-system,system-ui,sans-serif">${esc(letter)}</text>` : '';
  switch (shape) {
    case 'dot': return svg(`<circle cx="11" cy="8" r="5" fill="${c}" stroke="${e}" stroke-width="1"/>`);
    case 'ring': return svg(`<circle cx="11" cy="8" r="6" fill="none" stroke="${c}" stroke-width="2"/>`);
    case 'ringdot': return svg(`<circle cx="11" cy="8" r="5" fill="${c}" fill-opacity=".75" stroke="${e}" stroke-width="1.5"/>`);
    case 'halo': return svg(`<circle cx="11" cy="8" r="7" fill="${c}" fill-opacity=".2" stroke="${c}" stroke-width="1.6"/>`);
    case 'letter': return svg(`<circle cx="11" cy="8" r="7" fill="${c}" stroke="${e}" stroke-width="1"/>${t}`);
    case 'ringletter': return svg(`<circle cx="11" cy="8" r="6.5" fill="${e}" stroke="${c}" stroke-width="2"/>${t}`);
    case 'line': return svg(`<path d="M2 8h18" stroke="${c}" stroke-width="2.4" stroke-linecap="round"/>`);
    case 'dash': return svg(`<path d="M2 8h18" stroke="${c}" stroke-width="2" stroke-dasharray="3 2.5"/>`);
    case 'streak': return svg(`<defs><linearGradient id="g${c.slice(1)}"><stop offset="0" stop-color="${c}" stop-opacity="0"/><stop offset="1" stop-color="${c}"/></linearGradient></defs><path d="M1 11Q11 2 18 8" fill="none" stroke="url(#g${c.slice(1)})" stroke-width="2.4" stroke-linecap="round"/><circle cx="18" cy="8" r="2.4" fill="${c}"/>`);
    case 'area': return svg(`<rect x="3" y="2" width="16" height="12" rx="3" fill="${c}" fill-opacity=".45" stroke="${c}" stroke-width="1.2"/>`);
    case 'diamond': return svg(`<path d="M11 3l4.5 5-4.5 5-4.5-5z" fill="${c}"/>`);
    case 'plane': return svg(`<path d="M11 1.5l1.3 4.6 5.7 3.1v1.4l-5.7-1.6-.5 3.4 1.8 1.3v1l-2.6-.7-2.6.7v-1l1.8-1.3-.5-3.4-5.7 1.6V9.2l5.7-3.1z" fill="${c}" stroke="${e}" stroke-width=".6"/>`);
    case 'ship': return svg(`<path d="M11 2l3.5 5v7h-7V7z" fill="${c}" stroke="${e}" stroke-width=".8"/>`);
    case 'gradient': return svg(`<defs><linearGradient id="rg"><stop offset="0" stop-color="#9ad3ff"/><stop offset=".45" stop-color="#1e6fd9"/><stop offset=".75" stop-color="#ffd60a"/><stop offset="1" stop-color="#ff3b30"/></linearGradient></defs><rect x="2" y="4" width="18" height="8" rx="2" fill="url(#rg)"/>`);
    default: return '';
  }
}
const isDark = () => matchMedia('(prefers-color-scheme: dark)').matches;

// layers: the chip modules in chip order; on: which are switched on
// God's eye: the symbols that theme draws (eyeicons.js), with the same words; layers it does not redraw keep their key
const EYE = {
  aircraft: [['narrow', 'Airliner'], ['wide', 'Wide-body'], ['bizjet', 'Business jet'], ['turboprop', 'Turboprop'], ['light', 'Light aircraft'], ['heli_med', 'Helicopter'], ['note', 'Shape from the type code the aircraft broadcasts; small and simple when zoomed out']],
  military: [['fighter', 'Fighter', 'mil'], ['tanker', 'Tanker', 'mil'], ['strategic', 'Strategic airlifter', 'mil'], ['tactical', 'Tactical airlifter', 'mil'], ['awacs', 'Early warning', 'mil'], ['mpa', 'Patrol / surveillance', 'mil'], ['heli_med', 'Helicopter', 'mil'], ['mil_generic', 'Other military type', 'mil']],
  vip: [['vip', 'Government or VIP jet']], doomsday: [['doomsday', 'Command post (doomsday) plane']],
  unrest: [['clash', 'Armed clash'], ['smallarms', 'Small arms'], ['artillery', 'Artillery'], ['aerial', 'Air strike, drone'], ['attack', 'Attack'], ['bombing', 'Bombing'], ['assassin', 'Assassination'], ['protest', 'Protest'], ['riot', 'Riot'], ['note', 'Size = number of different outlets. Machine-coded from news, not verified.']],
  unrest1: [['protest', 'Reported by one outlet only (faded)']],
  quakes: [['quake_s', 'Under M4.5'], ['quake_m', 'M4.5 to 6'], ['quake_l', 'M6 and above'], ['quake_test', 'Within 50 km of a nuclear test site'], ['explosion', 'Explosion (USGS type)']],
  hazards: [['cyclone', 'Cyclone'], ['flood', 'Flood'], ['volcano', 'Volcano'], ['wildfire', 'Wildfire'], ['drought', 'Drought'], ['storm', 'Other (EONET)']],
  outages: [['outage', 'Internet outage (IODA)'], ['out_power', 'Cloudflare: power'], ['out_cable', 'Cloudflare: cable cut'], ['out_gov', 'Cloudflare: government'], ['out_mil', 'Cloudflare: military action']],
  ships: [['cargo', 'Cargo, or kind not given'], ['tanker_s', 'Tanker'], ['passenger', 'Passenger'], ['tug', 'Tug, port service'], ['sar', 'Pilot, search and rescue'], ['sailing', 'Sailing'], ['fishing', 'Fishing']],
  warships: [['warship_s', 'Warship (AIS)'], ['carrier', 'US carrier (USNI)'], ['amphib', 'US amphib (USNI)']],
  launches: [['launch', 'Launch pad, next days']], navwarn: [['nw_rocket', 'Rocket'], ['nw_missile', 'Missile firing'], ['nw_weapons', 'Weapons firing'], ['nw_exercise', 'Exercise'], ['nw_security', 'Security'], ['nw_gnss', 'GNSS interference']],
  bases: [['airbase', 'Air base'], ['navalbase', 'Naval base'], ['armybase', 'Military base'], ['radar', 'Radar'], ['sigint_site', 'Signals station'], ['missile_site', 'Missile site'], ['launchsite', 'Launch site'], ['ammo', 'Ammunition depot'], ['range', 'Training area'], ['milarea', 'Military area (OSM)']],
  nuclear: [['nuke', 'Power plant, operating'], ['nuke_build', 'Power plant, being built or planned'], ['nuke_off', 'Power plant, shut down'], ['reactor', 'Research reactor'], ['fuelcycle', 'Fuel cycle'], ['waste', 'Waste site'], ['uranium', 'Uranium mine'], ['testsite', 'Nuclear test site']],
  cameras: [['camera', 'Public camera'], ['camlive', 'Windy, live stream']], sdr: [['sdr', 'KiwiSDR receiver (faded: full)']],
  hotspots: [['hotspot', 'Hotspot: number = kinds of signal within 250 km in 24 h']], people: [['head', 'Head of state or government']],
};
export function renderLegend(el, layers, on) {
  const dk = isDark();
  if (eyeOn()) {
    const parts = layers.filter(l => on[l.id] && (EYE[l.id] || LEGENDS[l.id.toLowerCase()])).map(l => EYE[l.id]
      ? `<section><h4>${esc(l.title)}</h4><ul>${EYE[l.id].map(([g, t, ck]) => g === 'note' ? `<li class="lg-note">${esc(t)}</li>` : `<li>${glyphSvg(g, 20, dk, ck)}<span>${esc(t)}</span></li>`).join('')}</ul></section>`
      : `<section><h4>${esc(l.title)}</h4><ul>${LEGENDS[l.id.toLowerCase()].map(([shape, col, text, letter, alpha]) => shape === 'note' ? `<li class="lg-note">${esc(text)}</li>` : `<li>${swatch(shape, col ? col(dk) : '', letter || '', alpha ?? 1)}<span>${esc(text)}</span></li>`).join('')}</ul></section>`);
    (el.querySelector('.lg-body') || el).innerHTML = parts.join('') || '<p class="lg-note">Switch a layer on to see what its symbols mean.</p>';
    return;
  }
  const parts = layers.filter(l => on[l.id] && LEGENDS[l.id.toLowerCase()]).map(l => `<section><h4>${esc(l.title)}</h4><ul>${LEGENDS[l.id.toLowerCase()].map(([shape, col, text, letter, alpha]) =>
    shape === 'note' ? `<li class="lg-note">${esc(text)}</li>` : `<li>${swatch(shape, col ? col(dk) : '', letter || '', alpha ?? 1)}<span>${esc(text)}</span></li>`).join('')}</ul></section>`);
  (el.querySelector('.lg-body') || el).innerHTML = parts.join('') || '<p class="lg-note">Switch a layer on to see what its symbols mean.</p>';
}
