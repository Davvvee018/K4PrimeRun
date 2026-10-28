#!/usr/bin/env python3
"""Lightweight release gate to avoid shipping malformed K4 game files.

Uses Python stdlib + Node.js (available on GitHub Actions runners).
No browser/network dependency.
"""
from __future__ import annotations
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_png(path: Path, expected: int) -> None:
    data = path.read_bytes()
    expect(data[:8] == b'\x89PNG\r\n\x1a\n', f'Invalid PNG file {path}')
    width = int.from_bytes(data[16:20], 'big')
    height = int.from_bytes(data[20:24], 'big')
    expect((width, height) == (expected, expected), f'Wrong icon size {path}: {width}x{height}')


def main() -> None:
    html = (DIST/'index.html').read_text(encoding='utf-8')
    version = json.loads((DIST/'version.json').read_text(encoding='utf-8'))
    manifest = json.loads((DIST/'manifest.webmanifest').read_text(encoding='utf-8'))
    expect('K4 Prime Run' in html, 'Game metadata missing')
    expect((DIST/'CNAME').read_text(encoding='utf-8').strip() == 'k4runprime.ru', 'Custom domain mismatch')
    expect('https://k4runprime.ru/' in html, 'Custom domain metadata missing')
    expect(version['build'] in html, 'Build id mismatch')
    expect(manifest['display'] == 'standalone' and manifest['orientation'] == 'landscape', 'PWA metadata mismatch')
    expect('data-act="install"' in html, 'Install button missing')
    expect('function drawObstacles' in html, 'Obstacle renderer missing')
    expect('function drawTargets' in html, 'Drone renderer missing')
    expect('function drawBoss' in html, 'Boss renderer missing')
    expect('function drawProjectiles' in html, 'Projectile renderer missing')
    expect('function startGame' in html, 'Game startup function missing')
    expect('function shoot(' in html, 'Shooting logic missing')
    expect('function dash(' in html, 'Dash logic missing')
    expect('<script src="pwa.js" defer></script>' in html, 'PWA script missing')
    expect((DIST/'.nojekyll').is_file(), 'GitHub Pages .nojekyll marker missing')
    check_png(DIST/'icons/icon-192.png',192)
    check_png(DIST/'icons/icon-512.png',512)

    inline_scripts = [m for m in re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>', html, re.I) if m.strip()]
    expect(len(inline_scripts) == 1, f'Expected one inline game script, found {len(inline_scripts)}')
    with tempfile.TemporaryDirectory() as tmp:
        game_js = Path(tmp)/'game.js'
        game_js.write_text(inline_scripts[0], encoding='utf-8')
        for script in (game_js, DIST/'pwa.js', DIST/'sw.js'):
            subprocess.run(['node','--check', str(script)], check=True)

    print(f"OK: K4 Prime Run {version['version']} ({version['build']}), PWA assets and scripts valid")


if __name__ == '__main__':
    main()
