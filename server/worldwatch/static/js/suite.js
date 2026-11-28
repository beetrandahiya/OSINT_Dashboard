// The page switcher shared by every World Watch page: Map, Connections, Investigate, Sources.
export const PAGES = [['/', 'Map'], ['/connections', 'Connections'], ['/lookup', 'Investigate'], ['/feeds', 'Sources']];
export function suiteNav(active) {
  return `<nav class="suite-nav" aria-label="World Watch pages">${PAGES.map(([href, label]) =>
    `<a href="${href}"${label === active ? ' aria-current="page"' : ''}>${label}</a>`).join('')}</nav>`;
}
