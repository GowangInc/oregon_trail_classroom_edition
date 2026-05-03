/**
 * PWA support — register the service worker and log lifecycle events.
 */

(function () {
  if (!('serviceWorker' in navigator)) {
    console.log('[PWA] Service workers not supported on this browser.');
    return;
  }

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/static/sw.js')
      .then((registration) => {
        console.log('[PWA] Service worker registered:', registration.scope);
      })
      .catch((error) => {
        console.error('[PWA] Service worker registration failed:', error);
      });
  });
})();
