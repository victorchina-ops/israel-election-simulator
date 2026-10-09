/** Open About on a fresh visit, preserving explicit tab and component links. */
export function shouldOpenAbout(href) {
  if (!href) return false;
  const url = new URL(href, 'https://simulator.invalid/');
  return !url.searchParams.has('tab') && !/\/_data\/(?:charts|components)\//.test(url.pathname);
}
