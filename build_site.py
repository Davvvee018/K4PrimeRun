#!/usr/bin/env python3
"""Build a standalone, installable website from game/source.html.

GitHub Pages runs this on every push to main. No third-party dependencies.
"""
from __future__ import annotations
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
DIST = ROOT / 'dist'
SOURCE = ROOT / 'game' / 'source.html'
DOMAIN = (SITE / 'CNAME').read_text(encoding='utf-8').strip()


def main() -> None:
    game = SOURCE.read_text(encoding='utf-8')
    if not re.search(r'<html\b[^>]*lang="ru"', game, re.I):
        raise ValueError('Expected a complete Russian HTML game.')
    for essential in ['id="stage"', 'id="panel"', '<canvas', 'requestAnimationFrame(frame)']:
        if essential not in game:
            raise ValueError(f'Game is missing {essential}')
    version_match = re.search(r'K4\s+Prime\s+Run\s+([\d.]+)', game, re.I)
    version = version_match.group(1) if version_match else 'new'
    checksum = hashlib.sha256((game + (SITE / 'pwa.js').read_text() + (SITE / 'sw.js.in').read_text() + DOMAIN).encode('utf-8')).hexdigest()[:12]

    head = f'''<title>K4 Prime Run {version} — играть онлайн</title>
<meta name="theme-color" content="#0b1018">
<meta name="description" content="K4 Prime Run — футуристическая игра с 10 миссиями, дронами, боссами и фирменным оперативником K4 Prime. Играй на телефоне и компьютере.">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="K4 Run">
<meta name="mobile-web-app-capable" content="yes">
<meta name="k4-build" content="{checksum}">
<link rel="canonical" href="https://{DOMAIN}/">
<meta property="og:type" content="website">
<meta property="og:title" content="K4 Prime Run — играть онлайн">
<meta property="og:url" content="https://{DOMAIN}/">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">'''
    game, title_changes = re.subn(r'<title>.*?</title>', head, game, count=1, flags=re.I | re.S)
    if title_changes != 1:
        raise ValueError('Could not set page metadata.')

    css = '''<style id="k4-site-style">
.k4-standalone .install-link { display:none !important; }
#k4-update[hidden], #k4-popup[hidden] { display:none !important; }
#k4-update { position:fixed; left:50%; top:max(12px, env(safe-area-inset-top)); z-index:9999; transform:translateX(-50%); width:min(520px, calc(100vw - 24px)); box-sizing:border-box; padding:13px 16px; border:1px solid rgba(255,167,87,.46); border-radius:18px; background:rgba(10,15,25,.97); box-shadow:0 14px 40px #0008; color:#fff; font:500 14px/1.4 system-ui; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
#k4-update-text { flex:1; min-width:170px; }
#k4-update button, #k4-popup button { background:linear-gradient(120deg,#ffb35b,#ff7728); border:0; color:#101015; font:700 13px system-ui; padding:10px 15px; border-radius:999px; cursor:pointer; }
#k4-update #k4-close-update {background:#252f3d; color:#fff;}
#k4-popup { position:fixed; inset:0; z-index:10000; display:flex; justify-content:center; align-items:center; background:#03040bc9; padding:20px; box-sizing:border-box; color:#fff; font-family:system-ui; }
#k4-popup-inner { width:min(390px, 100%); border-radius:22px; padding:24px; box-sizing:border-box; background:linear-gradient(155deg,#242c3d,#0b0e16 70%); border:1px solid #ff9b513b; box-shadow:0 20px 60px #000a; text-align:center; }
#k4-popup strong { display:block; color:#ffb76d; font-size:19px; letter-spacing:.06em; margin:0 0 12px; }
#k4-popup-text { display:block; font-size:14px; line-height:1.6; margin:0 0 16px; }
#k4-popup button {min-width:130px;}
@media (max-height:450px) { #k4-update {top:5px; font-size:12px; padding:6px 10px} #k4-update button{padding:7px 10px;} }
</style>'''
    game = game.replace('</head>', css + '\n</head>', 1)

    # Make installation accessible from the existing menu, without changing game physics.
    menu_marker = "+bookLink(\"ghost\")+'</div></div>';"
    if menu_marker not in game:
        raise ValueError('Menu install button anchor has changed. Adjust builder for new game version.')
    game = game.replace(menu_marker, "+'<button class=\"ghost install-link\" type=\"button\" data-act=\"install\">Установить игру</button></div></div>';", 1)
    click_marker = '    if (a === "start") startGame(1);'
    if click_marker not in game:
        raise ValueError('Game action handler changed. Adjust builder to add install action.')
    game = game.replace(click_marker, '    if (a === "install") { if(window.K4Install) window.K4Install.request(); }\n    else if (a === "start") startGame(1);', 1)
    game = game.replace('</body>', '''<aside id="k4-update" hidden role="status" aria-live="polite">
  <span id="k4-update-text">Вышло обновление игры.</span>
  <button id="k4-apply-update" type="button">Обновить</button>
  <button id="k4-close-update" type="button" aria-label="Закрыть уведомление">Позже</button>
</aside>
<div id="k4-popup" hidden role="dialog" aria-modal="true" aria-label="Установка игры">
  <div id="k4-popup-inner"><strong>K4 PRIME RUN</strong><span id="k4-popup-text"></span><button id="k4-popup-close" type="button">Понятно</button></div>
</div>
<script src="pwa.js" defer></script>
</body>''', 1)

    DIST.mkdir(exist_ok=True)
    (DIST / 'index.html').write_text(game, encoding='utf-8')
    (DIST / 'pwa.js').write_bytes((SITE / 'pwa.js').read_bytes())
    (DIST / 'sw.js').write_text((SITE / 'sw.js.in').read_text(encoding='utf-8').replace('__BUILD__', checksum), encoding='utf-8')
    manifest = {
        'id': './',
        'name': 'K4 Prime Run',
        'short_name': 'K4 Run',
        'description': 'Футуристическая аркада K4 Prime: 10 миссий, дроны и боссы.',
        'start_url': './',
        'scope': './',
        'display': 'standalone',
        'orientation': 'landscape',
        'background_color': '#090e16',
        'theme_color': '#090e16',
        'lang': 'ru',
        'categories': ['games', 'entertainment'],
        'icons': [
            {'src': 'icons/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': 'icons/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
        ],
    }
    (DIST / 'manifest.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (DIST / 'version.json').write_text(json.dumps({'version': version, 'build': checksum}, ensure_ascii=False) + '\n', encoding='utf-8')
    (DIST / '.nojekyll').write_text('', encoding='utf-8')
    (DIST / 'CNAME').write_text(DOMAIN + '\n', encoding='utf-8')
    (DIST / 'icons').mkdir(exist_ok=True)
    for image in ('icon-192.png', 'icon-512.png'):
        shutil.copy2(SITE / 'icons' / image, DIST / 'icons' / image)
    shutil.copy2(SITE / 'apple-touch-icon.png', DIST / 'apple-touch-icon.png')
    print(f'Built K4 Prime Run {version}, build {checksum}; output {DIST}')


if __name__ == '__main__':
    main()
