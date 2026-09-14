// Shared Anees identity: favicon, installable-app metadata, and the visible header mark.
(function () {
  if (typeof document === 'undefined') return;
  const ownScript = document.currentScript || document.querySelector('script[src*="js/brand.js"]');
  if (!ownScript || !ownScript.src) return;
  const root = new URL('../', ownScript.src);

  function addLink(rel, href, sizes) {
    if (document.head.querySelector('link[rel="' + rel + '"]')) return;
    const link = document.createElement('link');
    link.rel = rel;
    link.href = new URL(href, root).href;
    if (sizes) link.sizes = sizes;
    document.head.appendChild(link);
  }

  addLink('icon', 'assets/favicon-32.png', '32x32');
  addLink('apple-touch-icon', 'assets/apple-touch-icon.png', '180x180');
  addLink('manifest', 'manifest.webmanifest');

  if (!document.head.querySelector('meta[name="theme-color"]')) {
    const theme = document.createElement('meta');
    theme.name = 'theme-color';
    theme.content = '#0F6E56';
    document.head.appendChild(theme);
  }

  if (!document.getElementById('anees-brand-style')) {
    const style = document.createElement('style');
    style.id = 'anees-brand-style';
    style.textContent = '.brand{align-items:center!important}.brand-logo{display:block;width:32px;height:32px;object-fit:contain;flex:0 0 32px}';
    document.head.appendChild(style);
  }

  document.querySelectorAll('.brand').forEach(function (brand) {
    if (brand.querySelector('.brand-logo')) return;
    const logo = document.createElement('img');
    logo.className = 'brand-logo';
    logo.src = new URL('assets/anees-logo.png', root).href;
    logo.alt = '';
    logo.width = 32;
    logo.height = 32;
    brand.prepend(logo);
  });
})();
