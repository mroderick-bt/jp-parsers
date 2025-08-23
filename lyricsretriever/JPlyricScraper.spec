# JPlyricScraper.spec
# -*- mode: python ; coding: utf-8 -*-
import sys
import inspect
from pathlib import Path

# Path to this .spec file
spec_path = Path(inspect.getframeinfo(inspect.currentframe()).filename).resolve()

# Repository root (one directory above lyricsretriever/)
REPO_ROOT = spec_path.parents[1]
sys.path.insert(0, str(REPO_ROOT))

a = Analysis(
    ['JPlyricScraper.py'],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[('C:/Users/untit/AppData/Local/Programs/Python/Python310/Lib/site-packages/pykakasi/data', 'pykakasi/data')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='JPlyricScraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
