/* K4 Prime Run: PWA installation and safe updates. */
(() => {
  'use strict';
  let deferredInstall = null;
  let registration = null;
  let refreshing = false;
  let foundVersion = null;
  const root = new URL('./', document.baseURI);
  const appVersion = document.querySelector('meta[name="k4-build"]')?.content || '';
  const popup = document.getElementById('k4-popup');
  const notice = document.getElementById('k4-update');
  const noticeText = document.getElementById('k4-update-text');
  const apply = document.getElementById('k4-apply-update');
  const closeUpdate = document.getElementById('k4-close-update');
  const popupText = document.getElementById('k4-popup-text');
  const popupClose = document.getElementById('k4-popup-close');

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  }
  if (isStandalone()) document.documentElement.classList.add('k4-standalone');

  function showPopup(message) {
    popupText.textContent = message;
    popup.hidden = false;
  }
  popupClose.addEventListener('click', () => { popup.hidden = true; });

  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferredInstall = event;
  });
  window.addEventListener('appinstalled', () => {
    deferredInstall = null;
    document.documentElement.classList.add('k4-standalone');
    popup.hidden = true;
  });

  window.K4Install = {
    request: async () => {
      if (isStandalone()) {
        showPopup('Игра уже установлена. Запускайте её с главного экрана устройства.');
        return;
      }
      if (deferredInstall) {
        const prompt = deferredInstall;
        deferredInstall = null;
        try { await prompt.prompt(); await prompt.userChoice; }
        catch (_) { showPopup('Откройте меню браузера и выберите «Установить приложение» или «На экран Домой».'); }
        return;
      }
      const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
      showPopup(ios
        ? 'На iPhone: откройте меню «Поделиться», выберите «На экран Домой» и нажмите «Добавить». Игра появится как отдельное приложение.'
        : 'Откройте меню браузера (⋮ или «Поделиться») и выберите «Установить приложение» либо «Добавить на главный экран».');
    }
  };

  function showNewVersion() {
    noticeText.textContent = 'Вышло обновление K4 Prime Run. Оно готово к установке.';
    notice.hidden = false;
  }
  function reloadForUpdate() {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    } else {
      location.reload();
    }
  }
  apply.addEventListener('click', reloadForUpdate);
  closeUpdate.addEventListener('click', () => { notice.hidden = true; });

  if ('serviceWorker' in navigator && ['https:', 'http:'].includes(location.protocol)) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!refreshing) { refreshing = true; location.reload(); }
    });
    window.addEventListener('load', () => {
      navigator.serviceWorker.register(new URL('sw.js', root).href, { updateViaCache: 'none' })
        .then(reg => {
          registration = reg;
          if (reg.waiting && navigator.serviceWorker.controller) showNewVersion();
          reg.addEventListener('updatefound', () => {
            const incoming = reg.installing;
            if (!incoming) return;
            incoming.addEventListener('statechange', () => {
              if (incoming.state === 'installed' && navigator.serviceWorker.controller) showNewVersion();
            });
          });
          reg.update().catch(() => {});
        })
        .catch(() => {});
    });
  }

  async function checkVersion() {
    if (document.hidden || !navigator.onLine || foundVersion) return;
    try {
      const response = await fetch(new URL('version.json?check=' + Date.now(), root), { cache: 'no-store' });
      if (!response.ok) return;
      const data = await response.json();
      if (data.build && data.build !== appVersion) {
        foundVersion = data.build;
        showNewVersion();
        registration?.update().catch(() => {});
      }
    } catch (_) { /* Offline mode is expected. */ }
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) checkVersion(); });
  window.addEventListener('focus', checkVersion);
  setInterval(checkVersion, 60 * 1000);
})();
